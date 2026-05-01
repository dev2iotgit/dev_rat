from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Employee, Device, AppSession, IdleSession, SecurityEvent, Shift, AgentCommand, AgentScreenshot, InstalledApp, BlacklistedApp, Attendance
from .serializers import DeviceSerializer
from .forms import ShiftForm
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count, Min, Max
import datetime
import os
import uuid
import base64
from django.core.files.base import ContentFile
from django.conf import settings
from .webhooks import send_security_alert
from .reports import generate_employee_report
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST

def get_session_shift_status(session, employee):
    """
    Returns 'on-shift', 'overtime', or 'off-shift' based on employee's shift.
    """
    if not employee or not employee.shift:
        return 'no-shift'
    
    shift = employee.shift
    # Session start/end are datetime objects
    session_start = session.start_time
    session_end = session.end_time
    
    # Check if working day
    day_name = session_start.strftime('%A').lower()
    is_workday = getattr(shift, day_name, False)
    
    if not is_workday:
        return 'off-shift'
        
    # Check times
    shift_start = shift.start_time
    shift_end = shift.end_time
    
    # Convert session times to time objects for comparison (ignoring date)
    st = session_start.time()
    et = session_end.time()
    
    # Simple check: on-shift if entirely within shift
    if st >= shift_start and et <= shift_end:
        return 'on-shift'
    
    # Overtime check: starts within shift but ends after
    if st >= shift_start and st < shift_end and et > shift_end:
        return 'overtime'
        
    # Off-shift: session starts after shift or ends before shift
    return 'off-shift'

@api_view(['POST'])
def register_device(request):
    machine_id = request.data.get('machine_id')
    os_username = request.data.get('os_username', 'Unknown User')
    
    if not machine_id:
        return Response({'error': 'machine_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
    # Standardize os_username as the employee identity
    employee, _ = Employee.objects.get_or_create(
        name=os_username,
        defaults={'department': 'Automated'}
    )

    device, created = Device.objects.get_or_create(
        machine_id=machine_id,
        defaults={
            'employee': employee,
            'os_name': request.data.get('os_name', 'Unknown'),
            'ip_address': request.data.get('ip_address')
        }
    )
    
    # Update device state if it existed but might have changed employees (shared machine)
    if not created:
        device.employee = employee
        device.os_name = request.data.get('os_name', device.os_name)
        device.ip_address = request.data.get('ip_address', device.ip_address)
        device.is_online = True
        device.save()
        
    serializer = DeviceSerializer(device)
    return Response({'agent_id': device.id, 'data': serializer.data}, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)

@api_view(['POST'])
def upload_app_sessions(request):
    agent_id = request.data.get('agent_id') # Leaving payload key as agent_id for backward compatibility with current agent script
    logs = request.data.get('logs', [])
    
    try:
        device = Device.objects.get(id=agent_id)
    except Device.DoesNotExist:
        return Response({'error': 'Invalid agent_id (device)'}, status=status.HTTP_404_NOT_FOUND)
        
    created_logs = []
    for log_data in logs:
        try:
            # Determine if this is an "Installed Application" vs system process
            clean_name = log_data.get('app_name', '').lower().replace('.exe', '')
            is_installed = False
            if clean_name:
                is_installed = InstalledApp.objects.filter(
                    device=device, 
                    app_name__icontains=clean_name
                ).exists()

            # Create session
            session = AppSession.objects.create(
                device=device,
                app_name=log_data.get('app_name'),
                is_installed_app=is_installed,
                start_time=log_data.get('start_time'),
                end_time=log_data.get('end_time'),
                duration=log_data.get('duration_seconds') or log_data.get('duration') or 0,
                data_rx_bytes=log_data.get('data_rx_bytes', 0),
                data_tx_bytes=log_data.get('data_tx_bytes', 0),
                disk_read_bytes=log_data.get('disk_read_bytes', 0),
                disk_write_bytes=log_data.get('disk_write_bytes', 0)
            )
            created_logs.append(session)
            
            # Cross-reference with InstalledApp to update 'last_used_at'
            # Update matching entries for this device
            InstalledApp.objects.filter(device=device, app_name__icontains=session.app_name).update(
                last_used_at=session.end_time
            )
        except Exception as e:
            print(f"Error logging session: {e}")
            
    return Response({'status': 'success', 'inserted': len(created_logs)}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def upload_security_events(request):
    agent_id = request.data.get('agent_id')
    events = request.data.get('logs', [])
    
    try:
        device = Device.objects.get(id=agent_id)
        device.last_seen = timezone.now()
        device.is_online = True
        device.save()
    except Device.DoesNotExist:
        return Response({'error': 'Invalid agent_id (device)'}, status=status.HTTP_404_NOT_FOUND)
        
    created_events = []
    for evt in events:
        evt_type = evt.get('event_type')
        if evt_type == 'idle':
            # Try to map idle events into the IdleSession model instead
            IdleSession.objects.create(
                device=device,
                idle_start=evt.get('timestamp'), # Close enough approximation until agent is updated
                idle_end=evt.get('timestamp'),   
                duration=evt.get('duration', 0)
            )
        else:
            # Generate risk weight dynamically (this is temporary, should be smarter)
            rw = 0
            if 'blacklist' in evt_type.lower(): rw = 40
            elif 'usb' in evt_type.lower(): rw = 10
            elif 'cpu' in evt_type.lower(): rw = 20
            
            new_evt = SecurityEvent.objects.create(
                device=device,
                event_type=evt_type,
                description=evt.get('description'),
                timestamp=evt.get('timestamp'),
                risk_weight=rw
            )
            created_events.append(new_evt)
            
            # Send Real-time Webhook if High Risk
            send_security_alert(new_evt)
        
    return Response({'status': 'success', 'inserted': len(created_events)}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def poll_commands(request):
    agent_id = request.GET.get('agent_id')
    try:
        device = Device.objects.get(id=agent_id)
        # Update heartbeat
        device.last_seen = timezone.now()
        device.is_online = True
        device.save()
        
        # Fetch pending commands
        commands = AgentCommand.objects.filter(device=device, status='pending')
        payload = []
        for cmd in commands:
            payload.append({
                'command_id': cmd.id,
                'type': cmd.command_type,
                'params': cmd.parameters
            })
            cmd.status = 'delivered'
            cmd.save()
        return Response({'commands': payload}, status=status.HTTP_200_OK)
    except Device.DoesNotExist:
        return Response({'error': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def update_command_result(request):
    command_id = request.data.get('command_id')
    status = request.data.get('status') # executed, failed
    message = request.data.get('message', '')
    
    try:
        cmd = AgentCommand.objects.get(id=command_id)
        cmd.status = status
        cmd.result_message = message
        cmd.save()
        return Response({'status': 'success'}, status=status.HTTP_200_OK)
    except AgentCommand.DoesNotExist:
        return Response({'error': 'Command not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def upload_screenshot(request):
    agent_id = request.data.get('agent_id')
    image_data = request.data.get('image_base64')
    command_id = request.data.get('command_id')
    
    try:
        device = Device.objects.get(id=agent_id)
        # Decode and save to filesystem
        format, imgstr = image_data.split(';base64,') 
        ext = format.split('/')[-1] 
        
        filename = f"screenshot_{agent_id}_{uuid.uuid4()}.{ext}"
        save_path = os.path.join(settings.MEDIA_ROOT, 'screenshots', filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, 'wb') as f:
            f.write(base64.b64decode(imgstr))
            
        # Create record
        # OPTIMIZATION: Use forward slashes for URLs to prevent broken images on Windows browsers
        AgentScreenshot.objects.create(
            device=device,
            image_path=os.path.join('screenshots', filename).replace('\\', '/')
        )
        
        # If this was linked to a command, mark it
        if command_id:
            cmd = AgentCommand.objects.filter(id=command_id).first()
            if cmd:
                cmd.status = 'executed'
                cmd.save()
                
        return Response({'status': 'success', 'path': filename}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@login_required
def dashboard_home(request):
    # Dynamic Offline Sweep
    threshold = timezone.now() - datetime.timedelta(minutes=3)
    Device.objects.filter(is_online=True, last_seen__lt=threshold).update(is_online=False)

    total_devices = Device.objects.count()
    online_devices = Device.objects.filter(is_online=True).count()
    offline_devices = total_devices - online_devices
    
    # Calculate company wide active time (Only Installed Apps)
    total_active_seconds = AppSession.objects.filter(is_installed_app=True).aggregate(Sum('duration'))['duration__sum'] or 0
    total_active_hours = round(total_active_seconds / 3600, 1)
    
    # Top 5 Used Applications (Only Installed Apps)
    top_apps = AppSession.objects.filter(is_installed_app=True).values('app_name').annotate(total_duration=Sum('duration')).order_by('-total_duration')[:5]
    
    # Total Tracked Hours per Agent (Device), summing up app session durations
    # As a rough metric for "total online hours per agent" requested.
    today = timezone.now().date()
    device_stats = []
    for d in Device.objects.all():
        # Overall (Only Installed Apps)
        active_total = AppSession.objects.filter(device=d, is_installed_app=True).aggregate(Sum('duration'))['duration__sum'] or 0
        idle_total = IdleSession.objects.filter(device=d).aggregate(Sum('duration'))['duration__sum'] or 0
        total_hours = round((active_total + idle_total) / 3600, 2)
        
        # Today (Only Installed Apps)
        active_today = AppSession.objects.filter(device=d, start_time__date=today, is_installed_app=True).aggregate(Sum('duration'))['duration__sum'] or 0
        idle_today = IdleSession.objects.filter(device=d, idle_start__date=today).aggregate(Sum('duration'))['duration__sum'] or 0
        today_hours = round((active_today + idle_today) / 3600, 2)
        
        # Shift Duration
        shift_duration = 0
        if d.employee and d.employee.shift:
            s = d.employee.shift
            start_dt = datetime.datetime.combine(today, s.start_time)
            end_dt = datetime.datetime.combine(today, s.end_time)
            if end_dt <= start_dt:
                end_dt += datetime.timedelta(days=1)
            shift_duration = round((end_dt - start_dt).total_seconds() / 3600, 1)

        # Latest Attendance Status
        latest_attendance = d.attendance_logs.order_by('-timestamp').first()
        attendance_status = latest_attendance.status if latest_attendance else "No Data"

        device_stats.append({
            'id': d.id,
            'machine_id': d.machine_id,
            'employee': d.employee.name if d.employee else 'Unassigned',
            'employee_id': d.employee.id if d.employee else None,
            'shift_name': d.employee.shift.name if (d.employee and d.employee.shift) else None,
            'is_online': d.is_online,
            'total_hours': total_hours,
            'today_hours': today_hours,
            'shift_duration': shift_duration,
            'attendance_status': attendance_status
        })
        
    # Recent Security alerts
    recent_alerts = SecurityEvent.objects.order_by('-timestamp')[:5]
    high_risk_count = Device.objects.filter(security_events__risk_weight__gt=50).distinct().count()
    
    # Shift Compliance Overview
    on_shift_sessions = 0
    overtime_sessions = 0
    off_shift_sessions = 0
    
    all_recent_sessions = AppSession.objects.order_by('-end_time')[:100]
    for sess in all_recent_sessions:
        status = get_session_shift_status(sess, sess.device.employee)
        if status == 'on-shift': on_shift_sessions += 1
        elif status == 'overtime': overtime_sessions += 1
        elif status == 'off-shift': off_shift_sessions += 1

    context = {
        'total_devices': total_devices,
        'online_devices': online_devices,
        'offline_devices': offline_devices,
        'total_active_hours': total_active_hours,
        'top_apps': top_apps,
        'device_stats': device_stats,
        'recent_alerts': recent_alerts,
        'high_risk_count': high_risk_count,
        'shift_summary': {
            'on_shift': on_shift_sessions,
            'overtime': overtime_sessions,
            'off_shift': off_shift_sessions
        },
        'all_shifts': Shift.objects.all(),
        'recent_attendance': Attendance.objects.order_by('-timestamp')[:5]
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax') == 'true':
        return render(request, 'tracker_api/_dashboard_content.html', context)
        
    return render(request, 'tracker_api/dashboard.html', context)

@login_required
def device_detail(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    
    # Dynamic Offline Sweep
    if device.is_online and timezone.now() - device.last_seen > datetime.timedelta(minutes=3):
        device.is_online = False
        device.save()
        
    # Grouped App Summary for Today (User's request)
    today = timezone.now().date()
    app_summary = AppSession.objects.filter(
        device=device, 
        start_time__date=today,
        is_installed_app=True
    ).values('app_name').annotate(
        count=Count('id'),
        total_duration=Sum('duration'),
        first_opened=Min('start_time'),
        last_active=Max('end_time')
    ).order_by('-last_active')

    # Last active cutoff for "LIVE" status (e.g., last 15 minutes)
    recent_cutoff = timezone.now() - datetime.timedelta(minutes=15)

    # Top apps (Only Installed Apps)
    top_apps = AppSession.objects.filter(device=device, is_installed_app=True).values('app_name').annotate(total_duration=Sum('duration')).order_by('-total_duration')[:10]
    # Recent Usage (Only Installed Apps)
    recent_logs = AppSession.objects.filter(device=device, is_installed_app=True).order_by('-end_time')[:30]
    # Agent Specific Events
    events = SecurityEvent.objects.filter(device=device).order_by('-timestamp')[:30]
    
    # Calculate Risk Score
    total_risk = SecurityEvent.objects.filter(device=device).aggregate(Sum('risk_weight'))['risk_weight__sum'] or 0
    if device.employee:
        device.employee.risk_score = total_risk
        device.employee.save()
        
    # Add shift status to each log
    decorated_logs = []
    for log in recent_logs:
        log.shift_status = get_session_shift_status(log, device.employee)
        decorated_logs.append(log)
        
    # Get Recent screenshots
    screenshots = AgentScreenshot.objects.filter(device=device).order_by('-timestamp')[:6]
    
    # Get recent commands status
    recent_commands = AgentCommand.objects.filter(device=device).order_by('-created_at')[:10]

    # Telemetry Overview Calculations (Only Installed Apps)
    today = timezone.now().date()
    active_total = AppSession.objects.filter(device=device, is_installed_app=True).aggregate(Sum('duration'))['duration__sum'] or 0
    idle_total = IdleSession.objects.filter(device=device).aggregate(Sum('duration'))['duration__sum'] or 0
    total_hours = round((active_total + idle_total) / 3600, 2)
    
    active_today = AppSession.objects.filter(device=device, start_time__date=today, is_installed_app=True).aggregate(Sum('duration'))['duration__sum'] or 0
    idle_today = IdleSession.objects.filter(device=device, idle_start__date=today).aggregate(Sum('duration'))['duration__sum'] or 0
    today_hours = round((active_today + idle_today) / 3600, 2)
    
    shift_duration = 0
    if device.employee and device.employee.shift:
        s = device.employee.shift
        start_dt = datetime.datetime.combine(today, s.start_time)
        end_dt = datetime.datetime.combine(today, s.end_time)
        if end_dt <= start_dt:
            end_dt += datetime.timedelta(days=1)
        shift_duration = round((end_dt - start_dt).total_seconds() / 3600, 1)

    today_productivity = 0
    if (active_today + idle_today) > 0:
        today_productivity = round((active_today / (active_today + idle_today)) * 100, 1)

    # Get Attendance Logs
    attendance_logs = device.attendance_logs.all().order_by('-timestamp')[:20]

    context = {
        'device': device,
        'top_apps': top_apps,
        'recent_logs': decorated_logs,
        'events': events,
        'risk_score': total_risk,
        'shift': device.employee.shift if device.employee else None,
        'screenshots': screenshots,
        'recent_commands': recent_commands,
        'total_hours': total_hours,
        'today_hours': today_hours,
        'shift_duration': shift_duration,
        'today_productivity': today_productivity,
        'app_summary': app_summary,
        'recent_cutoff': recent_cutoff,
        'attendance_logs': attendance_logs
    }
    return render(request, 'tracker_api/device_detail.html', context)

@user_passes_test(lambda u: u.is_superuser)
def dispatch_command(request, device_id):
    if request.method == 'POST':
        device = get_object_or_404(Device, id=device_id)
        cmd_type = request.POST.get('command_type')
        params_json = request.POST.get('parameters', '{}')
        
        import json
        try:
            params = json.loads(params_json)
        except:
            params = {}

        # Capture target_process explicitly if provided instead of JSON
        target_process = request.POST.get('target_process')
        if target_process:
            params['target'] = target_process

        # Support for burst screenshot or complex params from UI
        if cmd_type == 'screenshot' and 'count' not in params:
            # Default to 1 if not specified
            params['count'] = 1

        AgentCommand.objects.create(
            device=device,
            command_type=cmd_type,
            parameters=params,
            status='pending'
        )
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true':
            msg = f'Command {cmd_type} dispatched.'
            if cmd_type == 'screenshot' and params.get('count', 1) > 1:
                msg = f"Burst {params['count']}x Screenshot Audit dispatched."
            return JsonResponse({'status': 'success', 'message': msg})
            
    return redirect('device-detail', device_id=device_id)

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def bulk_archive_screenshots(request, device_id):
    try:
        select_all = request.POST.get('select_all') == 'true'
        screenshot_ids = request.POST.getlist('screenshot_ids')
        
        if select_all:
            count = AgentScreenshot.objects.filter(device_id=device_id, is_archived=False).update(
                is_archived=True, 
                archived_at=timezone.now()
            )
            return JsonResponse({'status': 'success', 'message': f'All {count} screenshots archived.'})
        elif screenshot_ids:
            count = AgentScreenshot.objects.filter(id__in=screenshot_ids, device_id=device_id).update(
                is_archived=True, 
                archived_at=timezone.now()
            )
            return JsonResponse({'status': 'success', 'message': f'{count} screenshots archived.'})
        return JsonResponse({'status': 'failed', 'message': 'No screenshots selected.'}, status=400)
    except Exception as e:
        print(f"[ERROR] bulk_archive_screenshots: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@api_view(['POST'])
def set_agent_offline(request):
    agent_id = request.data.get('agent_id')
    device = get_object_or_404(Device, id=agent_id)
    device.is_online = False
    device.save()
    return Response({'status': 'success', 'message': 'Agent marked offline.'})

@login_required
def device_usage_fragment(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    today = timezone.now().date()
    
    # App Summary for Today
    app_summary = AppSession.objects.filter(
        device=device, 
        start_time__date=today,
        is_installed_app=True
    ).values('app_name').annotate(
        count=Count('id'),
        total_duration=Sum('duration'),
        first_opened=Min('start_time'),
        last_active=Max('end_time')
    ).order_by('-last_active')

    # Recent cutoff for live status
    recent_cutoff = timezone.now() - datetime.timedelta(minutes=15)
    recent_logs = AppSession.objects.filter(device=device, is_installed_app=True).order_by('-end_time')[:30]
    
    # Calculate Top Apps for pie chart (Only Installed Apps)
    top_apps = AppSession.objects.filter(device=device, is_installed_app=True).values('app_name').annotate(total_duration=Sum('duration')).order_by('-total_duration')[:8]
    
    # Calculate Shift distribution
    shift_distribution = {
        'on_shift': 0,
        'off_shift': 0,
        'overtime': 0,
    }
    all_recent_logs = AppSession.objects.filter(device=device).order_by('-end_time')[:100]
    for log in all_recent_logs:
        status = get_session_shift_status(log, device.employee)
        if status == 'on-shift': shift_distribution['on_shift'] += log.duration
        elif status == 'off-shift': shift_distribution['off_shift'] += log.duration
        elif status == 'overtime': shift_distribution['overtime'] += log.duration
        
    # Add shift status to each log
    decorated_logs = []
    for log in recent_logs:
        log.shift_status = get_session_shift_status(log, device.employee)
        decorated_logs.append(log)
        
    return render(request, 'tracker_api/_recent_usage.html', {
        'device': device,
        'recent_logs': decorated_logs,
        'top_apps': top_apps,
        'shift_distribution': shift_distribution,
        'app_summary': app_summary,
        'recent_cutoff': recent_cutoff,
        'MEDIA_URL': settings.MEDIA_URL
    })

@login_required
def download_employee_report(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    pdf_content = generate_employee_report(employee)
    
    if pdf_content:
        response = HttpResponse(pdf_content, content_type='application/pdf')
        filename = f"Report_{employee.name}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    return HttpResponse("Error generating report", status=500)

@user_passes_test(lambda u: u.is_superuser)
def security_dashboard(request):
    # Determine riskiest devices/employees
    risky_devices = Device.objects.annotate(total_risk=Sum('security_events__risk_weight')).order_by('-total_risk')[:10]
    
    # Global security events
    recent_events = SecurityEvent.objects.order_by('-timestamp')[:100]
    
    # Event breakdown
    blacklist_count = SecurityEvent.objects.filter(event_type__icontains='blacklist').count()
    upload_spike_count = SecurityEvent.objects.filter(event_type__icontains='upload').count()
    disk_anomaly_count = SecurityEvent.objects.filter(event_type__icontains='disk').count()
    usb_count = SecurityEvent.objects.filter(event_type__icontains='usb').count()
    
    context = {
        'risky_devices': risky_devices,
        'recent_events': recent_events,
        'blacklist_count': blacklist_count,
        'upload_spike_count': upload_spike_count,
        'disk_anomaly_count': disk_anomaly_count,
        'usb_count': usb_count
    }
    return render(request, 'tracker_api/security_dashboard.html', context)

@user_passes_test(lambda u: u.is_superuser)
def analytics_dashboard(request):
    # Mock data for Z-Score and Time-Series
    total_active = AppSession.objects.aggregate(Sum('duration'))['duration__sum'] or 0
    total_idle = IdleSession.objects.aggregate(Sum('duration'))['duration__sum'] or 0
    
    if total_active + total_idle > 0:
        active_ratio = round((total_active / (total_active + total_idle)) * 100, 1)
        idle_ratio = round((total_idle / (total_active + total_idle)) * 100, 1)
    else:
        active_ratio = 0
        idle_ratio = 0
        
    # Focus Sessions (Duration > 25 mins: 1500s)
    focus_sessions_count = AppSession.objects.filter(duration__gte=1500).count()
    
    # Total context switches (total number of discrete app sessions)
    context_switches = AppSession.objects.count()
    
    # Heatmap data (Last 30 days)
    heatmap_data = []
    end_date = datetime.date.today()
    for i in range(29, -1, -1):
        day = end_date - datetime.timedelta(days=i)
        day_active = AppSession.objects.filter(
            start_time__date=day
        ).aggregate(Sum('duration'))['duration__sum'] or 0
        
        # Intensity level (0 to 4)
        intensity = 0
        if day_active > 18000: intensity = 4 # > 5h
        elif day_active > 10800: intensity = 3 # > 3h
        elif day_active > 3600: intensity = 2 # > 1h
        elif day_active > 0: intensity = 1
        
        heatmap_data.append({
            'date': day.strftime("%Y-%m-%d"),
            'intensity': intensity,
            'hours': round(day_active / 3600, 1)
        })

    context = {
        'active_ratio': active_ratio,
        'idle_ratio': idle_ratio,
        'focus_sessions_count': focus_sessions_count,
        'context_switches': context_switches,
        'heatmap_data': heatmap_data
    }
    return render(request, 'tracker_api/analytics_dashboard.html', context)

# Shift Management Views
@user_passes_test(lambda u: u.is_superuser)
def shift_list(request):
    shifts = Shift.objects.all()
    return render(request, 'tracker_api/shift_list.html', {'shifts': shifts})

@user_passes_test(lambda u: u.is_superuser)
def shift_create(request):
    if request.method == 'POST':
        form = ShiftForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('shift-list')
    else:
        form = ShiftForm()
    return render(request, 'tracker_api/shift_form.html', {'form': form, 'title': 'Create Shift'})

@user_passes_test(lambda u: u.is_superuser)
def shift_update(request, pk):
    shift = get_object_or_404(Shift, pk=pk)
    if request.method == 'POST':
        form = ShiftForm(request.POST, instance=shift)
        if form.is_valid():
            form.save()
            return redirect('shift-list')
    else:
        form = ShiftForm(instance=shift)
    return render(request, 'tracker_api/shift_form.html', {'form': form, 'title': 'Update Shift'})

@user_passes_test(lambda u: u.is_superuser)
def shift_delete(request, pk):
    shift = get_object_or_404(Shift, pk=pk)
    if request.method == 'POST':
        shift.delete()
        return redirect('shift-list')
    return render(request, 'tracker_api/shift_confirm_delete.html', {'shift': shift})

# Agent Alignment & Bulk Management
@user_passes_test(lambda u: u.is_superuser)
def employee_shift_align(request):
    if request.method == 'POST':
        employee_ids = request.POST.getlist('employee_ids')
        shift_id = request.POST.get('shift_id')
        
        if employee_ids and shift_id:
            shift = get_object_or_404(Shift, id=shift_id)
            Employee.objects.filter(id__in=employee_ids).update(shift=shift)
            return redirect('employee-shift-align')

    employees = Employee.objects.all().select_related('shift')
    shifts = Shift.objects.all()
    return render(request, 'tracker_api/employee_shift_align.html', {
        'employees': employees,
        'shifts': shifts
    })

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def quick_align_shift(request):
    employee_id = request.POST.get('employee_id')
    shift_id = request.POST.get('shift_id')
    
    employee = get_object_or_404(Employee, id=employee_id)
    if shift_id:
        shift = get_object_or_404(Shift, id=shift_id)
        employee.shift = shift
    else:
        employee.shift = None
    employee.save()
    
    return JsonResponse({
        'status': 'success', 
        'employee_name': employee.name,
        'shift_name': employee.shift.name if employee.shift else 'Unassigned'
    })

# AJAX Fragment Views for Real-time Monitoring
@login_required
def device_screenshots_fragment(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    # Hide archived screenshots from the live audit gallery
    screenshots = AgentScreenshot.objects.filter(device=device, is_archived=False).order_by('-timestamp')[:12]
    return render(request, 'tracker_api/_screenshots_gallery.html', {
        'device': device,
        'screenshots': screenshots,
        'MEDIA_URL': settings.MEDIA_URL
    })

@login_required
def device_commands_fragment(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    recent_commands = AgentCommand.objects.filter(device=device).order_by('-created_at')[:10]
    return render(request, 'tracker_api/_commands_trail.html', {
        'device': device,
        'recent_commands': recent_commands,
        'MEDIA_URL': settings.MEDIA_URL
    })

@login_required
def device_security_fragment(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    events = SecurityEvent.objects.filter(device=device).order_by('-timestamp')[:30]
    return render(request, 'tracker_api/_security_timeline.html', {
        'device': device,
        'events': events,
        'MEDIA_URL': settings.MEDIA_URL
    })

@api_view(['POST'])
def upload_installed_apps(request):
    agent_id = request.data.get('agent_id')
    apps_data = request.data.get('apps', [])
    
    device = get_object_or_404(Device, id=agent_id)
    
    # Efficiently sync apps
    # To keep it simple, we'll clear and recreate for a full sync.
    InstalledApp.objects.filter(device=device).delete()
    
    new_apps = []
    for app in apps_data:
        name = app.get('name')
        if not name: continue
        
        is_authorized = not BlacklistedApp.objects.filter(app_name__icontains=name).exists()
        new_apps.append(InstalledApp(
            device=device,
            app_name=name,
            version=app.get('version'),
            publisher=app.get('publisher'),
            install_date=app.get('install_date'),
            is_authorized=is_authorized
        ))
    
    InstalledApp.objects.bulk_create(new_apps)
    return Response({'status': 'success', 'count': len(new_apps)}, status=status.HTTP_201_CREATED)

@login_required
def device_apps_fragment(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    apps = InstalledApp.objects.filter(device=device).order_by('app_name')
    return render(request, 'tracker_api/_installed_apps.html', {'apps': apps})

@api_view(['GET', 'POST'])
def log_attendance(request):
    if request.method == 'GET':
        agent_id = request.GET.get('agent_id')
        if not agent_id:
            return Response({'error': 'agent_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            device = Device.objects.get(id=agent_id)
            logs = device.attendance_logs.all().order_by('-timestamp')[:10]
            data = [{'status': log.status, 'timestamp': log.timestamp.isoformat()} for log in logs]
            
            shift_end = None
            if device.employee and device.employee.shift:
                shift_end = device.employee.shift.end_time.strftime('%H:%M:%S')
                
            return Response({'logs': data, 'shift_end': shift_end}, status=status.HTTP_200_OK)
        except Device.DoesNotExist:
            return Response({'error': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

    agent_id = request.data.get('agent_id')
    status_val = request.data.get('status')
    
    if not agent_id or not status_val:
        return Response({'error': 'agent_id and status are required'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        device = Device.objects.get(id=agent_id)
        Attendance.objects.create(
            device=device,
            status=status_val
        )
        return Response({'status': 'success'}, status=status.HTTP_201_CREATED)
    except Device.DoesNotExist:
        return Response({'error': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

@login_required
def device_attendance_fragment(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    attendance_logs = device.attendance_logs.all().order_by('-timestamp')[:20]
    return render(request, 'tracker_api/_attendance_timeline.html', {'attendance_logs': attendance_logs})
