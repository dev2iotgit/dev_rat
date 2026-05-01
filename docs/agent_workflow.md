# Agent Workflow - `rat_agent`

The `rat_agent` is the edge component of the system. It is designed to be resilient, low-impact, and cross-platform.

## Main Entry Point (`main.py`)

When started, the agent performs the following steps:
1. **Initialize Database**: Sets up the local `local_logs.db` SQLite database if it doesn't exist.
2. **Start Monitors**: Spawns independent threads for telemetry collection.
3. **Start Sync Manager**: Spawns a thread to manage cloud synchronization.
4. **Start Local Reporter**: Spawns a local web server for proximity analytics.
5. **Idle Loop**: The main thread enters a sleep loop, waiting for a shutdown signal (Ctrl+C).

## Monitoring Modules

### 1. Application Monitor (`app_monitor.py`)
- **Frequency**: Polls every 1 second.
- **Mechanism**: Detects the currently active (foreground) window.
- **Captured Data**: 
    - Application name.
    - Start and end timestamps.
    - Network usage (Bytes RX/TX) per process.
    - Disk I/O (Read/Write) per process.
- **Logic**: When the active window changes, the current session is finalized and saved to the local DB, and a new session begins.

### 2. Idle Monitor (`idle_monitor.py`)
- **Frequency**: Continuous.
- **Mechanism**: Hooks into keyboard and mouse events using `pynput`.
- **Logic**: 
    - Tracks the "last activity" timestamp.
    - If `currentTime - lastActivity > threshold` (default 60s), the system enters "Idle" state.
    - Idle periods are recorded with start and end times.

### 3. Security Monitor (`security_monitor.py`)
- **Monitored Events**:
    - **USB Insertion/Removal**: Monitors hardware changes (WMI on Windows, `/sys` on Linux).
    - **Blacklisted Apps**: Checks running processes against a list of forbidden tools (e.g., `wireshark`, `nmap`).
    - **Anomalous Resource Usage**: Flags processes exceeding CPU thresholds or exhibiting ransomware-like disk write patterns.

## Synchronization Logic (`api_client.py`)

The `SyncManager` handles communication with the central server.

- **Registration**: On first run, the agent registers its hostname and OS to the server to obtain a unique `agent_id`. This ID is stored in `agent_id.txt`.
- **Sync Loop**: Every 60 seconds (configurable), the manager:
    1. Fetches all records from `local_logs.db` where `synced = 0`.
    2. **Concurrent Upload**: Logs are split into **chunks of 1,000**. These chunks are dispatched to a pool of **3 parallel workers** for high-throughput synchronization.
    3. On `201 Created` response, marks those records as synced in the local DB.
- **Offline Support**: If the server is unreachable, logs accumulate in the local SQLite database indefinitely until connectivity is restored.

## Local Reporter (`local_reporter.py`)

Allows the user (or local IT) to see activity status without cloud access.
- **Web URL**: `http://localhost:5050` (Basic Auth required).
- **CLI Mode**: Run `python local_reporter.py --cli` to print a text-based usage summary directly to the terminal.
- **Features**: Visualizes recent app usage and security alerts using Chart.js (Web) or ASCII tables (CLI).
