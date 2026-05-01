from django.urls import path
from . import views

urlpatterns = [
    # API endpoints
    path('api/agents/register/', views.register_device, name='api-register-device'),
    path('api/agents/offline/', views.set_agent_offline, name='api-agent-offline'),
    path('api/logs/apps/', views.upload_app_sessions, name='api-app-sessions'),
    path('api/logs/apps/installed/', views.upload_installed_apps, name='api-installed-apps'),
    path('api/logs/events/', views.upload_security_events, name='api-security-events'),
    path('api/commands/poll/', views.poll_commands, name='api-poll-commands'),
    path('api/commands/result/', views.update_command_result, name='api-command-result'),
    path('api/commands/screenshot/', views.upload_screenshot, name='api-upload-screenshot'),
    path('api/attendance/', views.log_attendance, name='api-attendance'),

    # Web Dashboard
    path('', views.dashboard_home, name='dashboard-home'),
    path('device/<int:device_id>/', views.device_detail, name='device-detail'),
    path('device/<int:device_id>/command/', views.dispatch_command, name='dispatch-command'),
    path('report/employee/<int:employee_id>/', views.download_employee_report, name='employee-report-download'),
    path('security/', views.security_dashboard, name='security-dashboard'),
    path('analytics/', views.analytics_dashboard, name='analytics-dashboard'),

    # Shift Management
    path('shifts/', views.shift_list, name='shift-list'),
    path('shifts/new/', views.shift_create, name='shift-create'),
    path('shifts/<int:pk>/edit/', views.shift_update, name='shift-update'),
    path('shifts/<int:pk>/delete/', views.shift_delete, name='shift-delete'),

    # Agent Alignment
    path('agents/align/', views.employee_shift_align, name='employee-shift-align'),
    path('agents/quick-align/', views.quick_align_shift, name='quick-align-shift'),

    # AJAX Fragments
    path('device/<int:device_id>/screenshots/', views.device_screenshots_fragment, name='device-screenshots-fragment'),
    path('device/<int:device_id>/screenshots/bulk-archive/', views.bulk_archive_screenshots, name='bulk-archive-screenshots'),
    path('device/<int:device_id>/commands/', views.device_commands_fragment, name='device-commands-fragment'),
    path('device/<int:device_id>/security/', views.device_security_fragment, name='device-security-fragment'),
    path('device/<int:device_id>/usage/', views.device_usage_fragment, name='device-usage-fragment'),
    path('device/<int:device_id>/apps/', views.device_apps_fragment, name='device-apps-fragment'),
    path('device/<int:device_id>/attendance/', views.device_attendance_fragment, name='device-attendance-fragment'),
]
