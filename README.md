# Project RAT - Remote Activity Tracker & Security Monitor

An enterprise-grade, cross-platform system for monitoring system activity, user productivity, and security threats. Consists of a Python-based client agent and a Django-powered centralized dashboard.

## 🚀 Key Features

- **Activity Tracking**: Per-application usage sessions with automatic window detection.
- **Productivity Analytics**: Active vs. Idle ratios, focus session tracking, and context-switching metrics.
- **Security Monitoring**: USB insertion tracking, blacklisted app detection, and anomalous resource usage alerts.
- **Live Audits & Real-time Monitoring**: Pure AJAX-driven live telemetry gallery and security timeline updates on device detail pages.
- **Offline Reliability**: Agents use local SQLite databases to cache logs when the cloud server is unreachable.
- **Advanced Dashboard**: Unified management view with behavioral risk scoring and trend graphs.
- **Maintenance & Health Tools**: Dedicated scripts for system-wide functionality checks and data cleanup.

## 📂 Project Structure

- `rat_agent/`: Python client responsible for local telemetry collection.
- `rat_web/`: Django server configuration and static assets.
- `tracker_api/`: Core Django application containing data models, REST API, and the Web Dashboard.
- `docs/`: Detailed technical documentation.

## 📖 Detailed Documentation

For a deep dive into the system, please refer to the following documents:

1. [**System Architecture**](docs/system_architecture.md) - High-level design and tech stack.
2. [**Agent Workflow**](docs/agent_workflow.md) - How the local telemetry agent operates.
3. [**Server Workflow**](docs/server_workflow.md) - Data processing, model schema, and dashboard logic.
4. [**API Reference**](docs/api_reference.md) - Communication protocol between Agent and Server.

## 🛠️ Quick Start

### 1. Requirements
- Python 3.10+
- Django 5.x
- `psutil`, `pynput`, `requests`, `python-dotenv`

### 2. Server Setup (`rat_web`)
```bash
# Install dependencies
pip install -r rat_web/requirements.txt

# Migrate Database
python manage.py migrate

# Create Superuser (for Dashboard access)
python manage.py createsuperuser

# Start Server
python manage.py runserver 0.0.0.0:8000
```

### 3. Agent Setup (`rat_agent`)
```bash
cd rat_agent
pip install -r requirements.txt

# Configure Server URL in .env
# SERVER_URL=http://your-server-ip:8000

# Run Agent
python main.py

# CLI Usage Report (Recent Activity)
python local_reporter.py --cli
```

## 🛠️ Maintenance & Utilities

The project includes several utility scripts to ensure system health and ease of management:

- `functionality_check.py`: Performs a full system audit (Server, API, and Agent) to ensure all components are communicating correctly.
- `clear_test_data.py`: Safely clears all telemetry, devices, and employees from the central server to allow for a fresh start.
- `rat_agent/clear_local_data.py`: Truncates the local agent database and resets device identity.

## 🛡️ License
Private Enterprise Software - All Rights Reserved.
