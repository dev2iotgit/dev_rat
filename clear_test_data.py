import os
import django
import shutil

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rat_web.settings')
django.setup()

from tracker_api.models import (
    Employee, Device, AppSession, IdleSession, SecurityEvent, 
    AgentCommand, AgentScreenshot, DailySummary, InstalledApp
)
from django.conf import settings

def clear_data():
    print(">>> Starting Server Data Cleanup...")
    
    # 1. Clear Telemetry & Logs
    print("Clearing App Sessions...")
    AppSession.objects.all().delete()
    
    print("Clearing Idle Sessions...")
    IdleSession.objects.all().delete()
    
    print("Clearing Security Events...")
    SecurityEvent.objects.all().delete()
    
    print("Clearing Daily Summaries...")
    DailySummary.objects.all().delete()
    
    print("Clearing Installed Apps Lists...")
    InstalledApp.objects.all().delete()
    
    # 2. Clear Commands & Screenshots
    print("Clearing Agent Commands...")
    AgentCommand.objects.all().delete()
    
    print("Clearing Screenshot Metadata...")
    AgentScreenshot.objects.all().delete()
    
    # 3. Clear Files
    screenshot_dir = os.path.join(settings.MEDIA_ROOT, 'screenshots')
    if os.path.exists(screenshot_dir):
        print(f"Deleting all files in {screenshot_dir}...")
        for filename in os.listdir(screenshot_dir):
            file_path = os.path.join(screenshot_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
    
    # 4. Clear Identity (Devices & Employees)
    print("Clearing Registered Devices...")
    Device.objects.all().delete()
    
    print("Clearing Employee Profiles...")
    Employee.objects.all().delete()
    
    print("\n>>> Server Cleanup Complete. System is now fresh.")

if __name__ == "__main__":
    clear_data()
