from django.contrib import admin
from .models import Agent, AppUsageLog, SystemEvent

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('machine_id', 'os_name', 'ip_address', 'last_seen')
    search_fields = ('machine_id', 'os_name')

@admin.register(AppUsageLog)
class AppUsageLogAdmin(admin.ModelAdmin):
    list_display = ('app_name', 'agent', 'start_time', 'duration', 'data_usage_bytes')
    list_filter = ('agent', 'app_name')
    search_fields = ('app_name', 'agent__machine_id')

@admin.register(SystemEvent)
class SystemEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'agent', 'timestamp', 'description')
    list_filter = ('event_type', 'agent')
    search_fields = ('description', 'agent__machine_id')
