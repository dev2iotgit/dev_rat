import requests
import json
import os

# Slack Configuration (In production, these would be in environment variables or DB)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

def send_security_alert(event):
    """
    Sends a formatted Slack message if the event risk weight is > 30.
    """
    if event.risk_weight <= 30:
        return # Skip low risk events

    if not SLACK_WEBHOOK_URL:
        print(f"[REPORTER] Slack webhook not configured. Skipping alert for {event.event_type}")
        return

    payload = {
        "text": f"🚨 *HIGH RISK SECURITY ALERT* 🚨\n*Type*: {event.event_type}\n*Employee*: {event.device.employee.name}\n*Device*: {event.device.machine_id}\n*Details*: {event.description}\n*Risk Weight*: {event.risk_weight}",
        "attachments": [
            {
                "color": "#ff0000",
                "fields": [
                    {
                        "title": "Agent ID",
                        "value": str(event.device.id),
                        "short": True
                    },
                    {
                        "title": "Time",
                        "value": event.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "short": True
                    }
                ]
            }
        ]
    }

    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"[ERROR] Failed to send Slack alert: {e}")
