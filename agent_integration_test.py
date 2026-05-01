import requests
import time
import uuid

SERVER_URL = "http://localhost:8000"

def test_agent_integration():
    print("--- Agent-to-Server Connectivity Test ---")
    
    # 1. Registration
    machine_id = f"TEST-NODE-{uuid.uuid4().hex[:6]}"
    print(f"[1] Registering agent: {machine_id}...")
    try:
        reg_resp = requests.post(f"{SERVER_URL}/api/agents/register/", json={
            "machine_id": machine_id,
            "os_name": "TestEnvironment",
            "ip_address": "127.0.0.1",
            "os_username": "INTEGRATION_TEST_USER"
        }, timeout=5)
    except Exception as e:
        print(f"FAILED to reach server: {e}")
        return

    if reg_resp.status_code not in [200, 201]:
        print(f"FAILED: Registration returned {reg_resp.status_code} - {reg_resp.text}")
        return
    
    agent_id = reg_resp.json().get('agent_id')
    print(f"SUCCESS: Registered! Agent ID: {agent_id}")

    # 2. Log Submission
    print(f"[2] Submitting app logs for Agent {agent_id}...")
    log_payload = {
        "agent_id": agent_id,
        "logs": [{
            "app_name": "IntegrationTester.exe",
            "start_time": "2026-04-16T10:00:00Z",
            "end_time": "2026-04-16T10:05:00Z",
            "duration_seconds": 300
        }]
    }
    log_resp = requests.post(f"{SERVER_URL}/api/logs/apps/", json=log_payload, timeout=5)
    if log_resp.status_code == 201:
        print("SUCCESS: App logs submitted successfully.")
    else:
        print(f"FAILED: Log submission returned {log_resp.status_code} - {log_resp.text}")

    # 3. Command Polling
    print(f"[3] Polling for commands...")
    poll_resp = requests.get(f"{SERVER_URL}/api/commands/poll/", params={"agent_id": agent_id}, timeout=5)
    if poll_resp.status_code == 200:
        commands = poll_resp.json().get('commands', [])
        print(f"SUCCESS: Polling successful. Pending commands found: {len(commands)}")
    else:
        print(f"FAILED: Polling returned {poll_resp.status_code}")

    print("\n--- Agent Verification Complete ---")

if __name__ == "__main__":
    test_agent_integration()
