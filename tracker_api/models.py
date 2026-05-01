from django.db import models

class Shift(models.Model):
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Working Days
    monday = models.BooleanField(default=True)
    tuesday = models.BooleanField(default=True)
    wednesday = models.BooleanField(default=True)
    thursday = models.BooleanField(default=True)
    friday = models.BooleanField(default=True)
    saturday = models.BooleanField(default=False)
    sunday = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"

class Employee(models.Model):
    name = models.CharField(max_length=255)
    department = models.CharField(max_length=255, null=True, blank=True)
    shift = models.ForeignKey(Shift, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    risk_score = models.IntegerField(default=0, help_text="Calculated behavioral risk score")
    
    def __str__(self):
        return f"{self.name} ({self.department})"

class Device(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='devices')
    machine_id = models.CharField(max_length=255, unique=True)
    os_name = models.CharField(max_length=50)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    is_online = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.machine_id} - {self.employee.name if self.employee else 'Unassigned'}"

class AppSession(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='app_sessions')
    app_name = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration = models.IntegerField(help_text="Duration in seconds")
    is_installed_app = models.BooleanField(default=False, help_text="True if this matches an entry in InstalledApp")
    
    # Network & Storage Metrics
    data_rx_bytes = models.BigIntegerField(default=0, help_text="Network Download")
    data_tx_bytes = models.BigIntegerField(default=0, help_text="Network Upload")
    disk_read_bytes = models.BigIntegerField(default=0)
    disk_write_bytes = models.BigIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.duration}s] {self.app_name} on {self.device.machine_id}"

class IdleSession(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='idle_sessions')
    idle_start = models.DateTimeField()
    idle_end = models.DateTimeField()
    duration = models.IntegerField(help_text="Duration in seconds")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Idle for {self.duration}s on {self.device.machine_id}"

class SecurityEvent(models.Model):
    # Events: usb_insertion, usb_removal, blacklisted_app, high_cpu_process, high_upload_spike, disk_write_anomaly
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='security_events')
    event_type = models.CharField(max_length=50) 
    description = models.TextField()
    timestamp = models.DateTimeField()
    risk_weight = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.event_type}] on {self.device.machine_id}"

class AgentCommand(models.Model):
    COMMAND_CHOICES = (
        ('lock', 'Lock Workstation'),
        ('screenshot', 'Capture Screenshot'),
        ('terminate', 'Terminate Process'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('delivered', 'Delivered'),
        ('executed', 'Executed'),
        ('failed', 'Failed'),
    )
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='commands')
    command_type = models.CharField(max_length=50, choices=COMMAND_CHOICES)
    parameters = models.JSONField(null=True, blank=True, help_text="e.g. {'pid': 1234}")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    result_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.command_type} for {self.device.machine_id} ({self.status})"

class AgentScreenshot(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='screenshots')
    image_path = models.CharField(max_length=500)
    trigger_event = models.ForeignKey('SecurityEvent', on_delete=models.SET_NULL, null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Screenshot from {self.device.machine_id} at {self.timestamp}"

class DailySummary(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='daily_summaries')
    date = models.DateField()
    total_active_seconds = models.IntegerField(default=0)
    total_idle_seconds = models.IntegerField(default=0)
    productivity_score = models.FloatField(default=0.0)
    context_switches = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('employee', 'date')

    def __str__(self):
        return f"Summary for {self.employee.name} on {self.date}"

class InstalledApp(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='installed_apps')
    app_name = models.CharField(max_length=255)
    version = models.CharField(max_length=100, null=True, blank=True)
    publisher = models.CharField(max_length=255, null=True, blank=True)
    install_date = models.CharField(max_length=100, null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    is_authorized = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('device', 'app_name')

    def __str__(self):
        return f"{self.app_name} on {self.device.machine_id}"

class BlacklistedApp(models.Model):
    app_name = models.CharField(max_length=255, unique=True, help_text="Exact name of the application to flag as unauthorized")
    risk_weight = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)

class Attendance(models.Model):
    STATUS_CHOICES = (
        ('check-in', 'Check-In'),
        ('check-out', 'Check-Out'),
        ('break-start', 'Break Start'),
        ('break-end', 'Break End'),
    )
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='attendance_logs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.device.machine_id} - {self.status} at {self.timestamp}"
