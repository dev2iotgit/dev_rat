from django.test import TestCase, Client
from django.urls import reverse
from tracker_api.models import Device, Employee, AppSession, Shift
import json

class DeviceRegistrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('api-register-device')

    def test_new_device_registration(self):
        """Test that a new device creates a new employee based on os_username."""
        payload = {
            "machine_id": "WS-001",
            "os_name": "Windows",
            "os_username": "bob_admin"
        }
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Employee.objects.count(), 1)
        self.assertEqual(Employee.objects.first().name, "bob_admin")
        self.assertEqual(Device.objects.count(), 1)

    def test_duplicate_employee_unification(self):
        """Test that two different devices with the same os_username link to ONE employee."""
        # First device
        self.client.post(self.url, data=json.dumps({
            "machine_id": "WS-001", "os_username": "bob_admin"
        }), content_type='application/json')
        
        # Second device
        self.client.post(self.url, data=json.dumps({
            "machine_id": "WS-002", "os_username": "bob_admin"
        }), content_type='application/json')
        
        self.assertEqual(Employee.objects.count(), 1, "Should only have ONE employee record")
        self.assertEqual(Device.objects.count(), 2, "Should have TWO devices linked to the same employee")

    def test_shared_machine_handover(self):
        """Test that if a new user logs into an existing machine, the machine ownership updates."""
        # Bob registers machine WS-001
        self.client.post(self.url, data=json.dumps({
            "machine_id": "WS-001", "os_username": "bob"
        }), content_type='application/json')
        
        # Alice logs into same machine WS-001
        self.client.post(self.url, data=json.dumps({
            "machine_id": "WS-001", "os_username": "alice"
        }), content_type='application/json')
        
        self.assertEqual(Employee.objects.count(), 2)
        device = Device.objects.get(machine_id="WS-001")
        self.assertEqual(device.employee.name, "alice", "Machine should now belong to Alice")

class DashboardSecurityTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.manager = User.objects.create_user(username='manager', password='password')
        self.admin = User.objects.create_superuser(username='admin', password='password')
        self.client = Client()

    def test_unauthenticated_redirect(self):
        """Verify dashboard requires login."""
        response = self.client.get(reverse('dashboard-home'))
        self.assertEqual(response.status_code, 302)

    def test_manager_access_restrictions(self):
        """Verify standard manager cannot access advanced dashboards."""
        self.client.login(username='manager', password='password')
        
        # Security Dashboard
        response = self.client.get(reverse('security-dashboard'))
        self.assertEqual(response.status_code, 302, "Manager should be redirected from Security Center")
        
        # Analytics Dashboard
        response = self.client.get(reverse('analytics-dashboard'))
        self.assertEqual(response.status_code, 302, "Manager should be redirected from Advanced Analytics")

    def test_admin_full_access(self):
        """Verify superuser has full access."""
        self.client.login(username='admin', password='password')
        
        response = self.client.get(reverse('security-dashboard'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('analytics-dashboard'))
        self.assertEqual(response.status_code, 200)
