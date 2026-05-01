# Server Workflow - `rat_web`

The `rat_web` server (powered by Django) acts as the central intelligence hub, aggregating telemetry from all agents and providing actionable insights.

## Core Data Models (`tracker_api/models.py`)

The system uses a relational schema to track employees and their digital footprints:

- **`Employee`**: The human entity. Tracks department, assigned **Shift**, and an aggregate **Behavioral Risk Score**.
- **`Shift`**: Defines working hours (Start/End) and working days (Mon-Sun).
- **`Device`**: The machine running the agent. Linked to an Employee. Tracks machine ID, OS, and "Last Seen" status.
- **`AppSession`**: Records of application usage. Includes duration, network throughput (RX/TX), and Disk I/O.
- **`IdleSession`**: Records of inactivity periods per device.
- **`SecurityEvent`**: Log of alerts (USB, Blacklists, Anomalies). Each event carries a `risk_weight`.
- **`DailySummary`**: Pre-aggregated daily stats (Total Active, Total Idle, Productivity Score).

## API Processing (`tracker_api/views.py`)

The server handles incoming data through specialized DRF views:

1. **`register_device` (Auto-Identity)**: 
    - Finds or creates a `Device` record based on the `machine_id`.
    - **Each agent is considered an employee**: If no `Employee` is linked to the device, the system automatically creates a new Employee profile using the `machine_id` as the name.
    - Updates IP address and OS information.
    - Sets `is_online = True`.

2. **`poll_commands`**: 
    - Agents hit this every 5 seconds.
    - Returns pending `AgentCommand` objects (Lock, Screenshot, Terminate).
    - Status transitions from `pending` -> `delivered`.

3. **`upload_screenshot`**: 
    - Handles base64 encoded screen captures.
    - Stores images on the **filesystem** (`/media/screenshots/`).
    - Links the capture to the requesting command or security event.

4. **`logs_apps`**:
    - Processes incoming batches (up to 1,000 logs per chunk).
    - Creates multiple `AppSession` records.
    - Updates `last_used_at` timestamps for matching `InstalledApp` entries.
    - Links logs to the correct `Device`.

5. **`logs_events`**:
    - Processes security and idle events.
    - Maps "idle" type events to the `IdleSession` model.
    - Assigns dynamic `risk_weight` based on the event type (e.g., Blacklisted App = 40, USB = 10).

## Dashboard & Analytics

The dashboard calculates metrics in real-time or via aggregation:

### 1. Productivity & Shift Compliance
- **Daily Heatmap**: Visualizes organization-wide activity levels over the last 30 days.
- **Weekly PDF Reporting**: Automated generation of activity summaries for HR/Management.
...
### 4. Remote Control & Remediation
- **On-Demand Actions**: Lock workstation, Capture Screenshot, Kill Process.
- **Auto-Suspension**: Suspicious Ransomware-like processes are automatically flagged by the agent.
- **Bulk Sync**: The `upload_installed_apps` API uses `bulk_create` to efficiently sync thousands of software inventory items in a single transaction.
- **Slack Alerts**: Real-time notifications for every event with a `risk_weight > 30`.
- **Context Switching**: Tracks the number of discrete application sessions per hour.

### 2. Behavioral Risk Scoring
Each employee's risk score is calculated by summing the weights of their security events:
- **Blacklisted Tool**: 40 points.
- **High CPU/Suspicious Process**: 20 points.
- **USB Insertion**: 10 points.
- **High Upload Spike**: (Logic planned for future implementation).

### 3. Anomaly Detection (Planned)
- Implementation of **Z-Score analysis** to flag employees whose activity deviates significantly from their historical mean (e.g., a sudden 500% increase in network uploads).
