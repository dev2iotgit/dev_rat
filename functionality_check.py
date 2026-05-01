import subprocess
import time
import sys
import os
import requests
import uuid
import signal

# Configuration
SERVER_URL = "http://localhost:8000"
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_WEB_PYTHON = os.path.join(PROJECT_ROOT, "venv_web", "Scripts", "python.exe")
VENV_AGENT_PYTHON = os.path.join(PROJECT_ROOT, "rat_agent", "venv", "Scripts", "python.exe")

def run_step(name, func):
    print(f"\n>>> Step: {name}")
    try:
        success = func()
        if success:
            print(f"PASSED: {name}")
            return True
        else:
            print(f"FAILED: {name}")
            return False
    except Exception as e:
        print(f"ERROR: {name} - {str(e)}")
        return False

def check_envs():
    if not os.path.exists(VENV_WEB_PYTHON):
        print(f"Error: {VENV_WEB_PYTHON} not found.")
        return False
    if not os.path.exists(VENV_AGENT_PYTHON):
        print(f"Error: {VENV_AGENT_PYTHON} not found.")
        return False
    return True

def start_server():
    print("Starting Django server in background...")
    proc = subprocess.Popen([VENV_WEB_PYTHON, "manage.py", "runserver", "8000"], 
                            cwd=PROJECT_ROOT, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE,
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
    
    # Wait for server to be ready
    for _ in range(30):
        try:
            resp = requests.get(SERVER_URL, timeout=2)
            if resp.status_code == 200:
                print("Server is up and running.")
                return proc
        except:
            time.sleep(1)
    
    print("Server failed to start within 30 seconds.")
    proc.terminate()
    return None

def test_api_integration():
    machine_id = f"FUNC-TEST-{uuid.uuid4().hex[:6]}"
    print(f"Registering test agent: {machine_id}...")
    
    # 1. Registration
    reg_resp = requests.post(f"{SERVER_URL}/api/agents/register/", json={
        "machine_id": machine_id,
        "os_name": "FuncCheckEnv",
        "ip_address": "127.0.0.1",
        "os_username": "FUNC_CHECK_USER"
    }, timeout=5)
    
    if reg_resp.status_code not in [200, 201]:
        print(f"Registration failed: {reg_resp.text}")
        return False
    
    agent_id = reg_resp.json().get('agent_id')
    print(f"Agent registered with ID: {agent_id}")

    # 2. App Logs
    print("Submitting test app logs...")
    log_payload = {
        "agent_id": agent_id,
        "logs": [{
            "app_name": "FunctionalityChecker.py",
            "start_time": "2026-04-17T11:00:00Z",
            "end_time": "2026-04-17T11:05:00Z",
            "duration_seconds": 300
        }]
    }
    log_resp = requests.post(f"{SERVER_URL}/api/logs/apps/", json=log_payload, timeout=5)
    if log_resp.status_code != 201:
        print(f"Log submission failed: {log_resp.text}")
        return False

    # 3. Command Polling
    print("Polling for commands...")
    poll_resp = requests.get(f"{SERVER_URL}/api/commands/poll/", params={"agent_id": agent_id}, timeout=5)
    if poll_resp.status_code != 200:
        print(f"Command poll failed: {poll_resp.status_code}")
        return False
    
    return True

def run_agent_unit_tests():
    print("Running Agent unit tests via pytest...")
    # Run pytest from inside rat_agent directory to ensure imports work correctly
    res = subprocess.run([VENV_AGENT_PYTHON, "-m", "pytest", "tests/"], 
                         cwd=os.path.join(PROJECT_ROOT, "rat_agent"), capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(res.stderr)
    return res.returncode == 0

def check_dashboard():
    print("Checking Dashboard accessibility...")
    resp = requests.get(SERVER_URL, timeout=5)
    return resp.status_code == 200

def main():
    if not run_step("Verify Environments", check_envs):
        sys.exit(1)
        
    server_proc = start_server()
    if not server_proc:
        sys.exit(1)
    
    try:
        results = []
        results.append(run_step("API Integration", test_api_integration))
        results.append(run_step("Agent Unit Tests", run_agent_unit_tests))
        results.append(run_step("Dashboard Access", check_dashboard))
        
        if all(results):
            print("\n===============================")
            print("   ALL FUNCTIONALITY CHECKS PASSED   ")
            print("===============================\n")
        else:
            print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("   SOME CHECKS FAILED   ")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
            
    finally:
        print("Shutting down Django server...")
        if os.name == 'nt':
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(server_proc.pid)], capture_output=True)
        else:
            os.killpg(os.getpgid(server_proc.pid), signal.SIGTERM)
        print("Done.")

if __name__ == "__main__":
    main()
