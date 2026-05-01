from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.db.models import Sum
from .models import AppSession, SecurityEvent, Device
import datetime

def generate_employee_report(employee):
    """
    Generates a PDF report summary for an employee.
    """
    devices = Device.objects.filter(employee=employee)
    
    # Calculate stats
    total_active_seconds = AppSession.objects.filter(device__in=devices).aggregate(Sum('duration'))['duration__sum'] or 0
    total_active_hours = round(total_active_seconds / 3600, 2)
    
    top_apps = AppSession.objects.filter(device__in=devices).values('app_name').annotate(total_duration=Sum('duration')).order_by('-total_duration')[:5]
    
    recent_events = SecurityEvent.objects.filter(device__in=devices).order_by('-timestamp')[:20]
    
    context = {
        'employee': employee,
        'report_date': datetime.datetime.now().strftime("%Y-%m-%d"),
        'total_active_hours': total_active_hours,
        'top_apps': top_apps,
        'recent_events': recent_events
    }
    
    # Render template to HTML
    template = get_template('tracker_api/reports/employee_report_template.html')
    html = template.render(context)
    
    # Create PDF
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        return result.getvalue()
    return None
