from django.core.management.base import BaseCommand
from django.utils import timezone
from tracker_api.models import AgentScreenshot
import os
import datetime
from django.conf import settings

class Command(BaseCommand):
    help = 'Permanently deletes archived screenshots older than 7 days'

    def handle(self, *args, **options):
        # 7 days ago
        cutoff = timezone.now() - datetime.timedelta(days=7)
        
        # Find archived screenshots older than 7 days
        old_screenshots = AgentScreenshot.objects.filter(
            is_archived=True,
            archived_at__lt=cutoff
        )
        
        count = old_screenshots.count()
        self.stdout.write(f"Found {count} screenshots to permanently delete.")
        
        for screen in old_screenshots:
            # Delete physical file
            full_path = os.path.join(settings.MEDIA_ROOT, screen.image_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                self.stdout.write(f"Deleted file: {screen.image_path}")
            
            # Delete DB record
            screen.delete()
            
        self.stdout.write(self.style.SUCCESS(f"Successfully cleaned up {count} archived screenshots."))
