# Enterprise Linux Activity & Security Monitoring System - Implementation Plan

This document outlines the architecture for the cross-platform activity tracker agent and the server-side Django REST application, encompassing advanced productivity and security analytics.

## 1. Django Server (`rat_web`)

The server acts as the cloud data lake and provides an enterprise-grade dashboard interface to view the logs collected from multiple agents.

### Data Model Concept
To support the advanced tracking metrics, the Django models will be expanded:
- `Employee`: Represents the user.
- `Device` (`Agent`): Represents the machine, linked to an Employee.
- `AppSession` (`AppUsageLog`): App start time, end time, duration.
- `IdleSession`: Specific model tracking `idle_start`, `idle_end`, `duration`.
- `NetworkUsage`: RX/TX bytes relational to AppSessions.
- `SecurityEvent`: Idle trigger, USB insertions, Blacklisted App matches, Suspicious Process alerts.
- `DailySummary`: Aggregated analytic rollups (e.g. Total Active, Total Idle) for performance indexing.

### Dashboard Requirements
1. **Main Overview Page & Organization-Level Stats**
   - Active/Idle employees, separate count of Online/Offline devices, Total Online Hours per agent.
   - Company-wide active time, Department Productivity Comparisons, and Top 10 applications today.
   - **Productivity Heatmap**: Calendar view (Hours vs Days) color-coded by Productivity %.
   - **Security Trend Graph**: Weekly incidents, Monthly blacklist attempts, Risk growth curve.
2. **Employee Detail Page**
   - Current active app, active duration, idle timer, and CPU/Network stats.
   - App usage timeline block chart and Idle session history.
3. **Security Dashboard & Behavioral Risk Scoring**
   - Alert timeline (Blacklisted apps, USB activity, CPU spikes).
   - **Disk Usage & Network Anomalies**: Track Disk I/O Write anomalies (Ransomware patterns) and Network `Upload/(Upload+Download)` Ratios (>70% flagged as Exfiltration).
   - **Insider Threat / Burnout Indicator**: Flag employees with high active time + low breaks + after-hours activity.
   - **Advanced Risk Score per Employee**: 
     - Calculated dynamically: `(Blacklisted tool * 40) + (High Upload * 30) + (Suspicious CPU * 20) + (USB Insert * 10)`.
4. **Analytics Page (Productivity & Advanced Models)**
   - **Productivity Statistics**:
     - *App Usage Distribution*, *Active vs Idle Ratio* (Pie chart/trend line).
     - *Focus Score*: Track deep work (Uninterrupted use > 25 mins) vs *Context Switching Rate* (>30 switches/hr flagged).
   - **Advanced Statistical Models**:
     - *Z-Score Anomaly Detection*: Flag anomalies where `Z = (Current - Mean) / StdDev > 2.5`.
     - *Time-Series Forecasting*: Predict expected upload/CPU/app behavior and flag sharp deviations.

---

## 2. Python Console Agent (`rat_agent`)

The agent tracks employee system activity natively on both **Windows and Linux (including Wayland and X11)** environments, works entirely offline via SQLite (`local_logs.db`), and syncs to the backend REST API when available.

### Modules:
1. **Application Monitoring (`app_monitor.py`)**
   - Detects current active application via `psutil`.
   - Logs App start/end time and exact duration.
   - Tracks per-process network usage (RX/TX bytes).
2. **Idle Detection (`idle_monitor.py`)**
   - Monitors keyboard/mouse input via `pynput` (With specific multi-display & Wayland compat layers like `dbus` checks if needed).
   - Logs exact idle session boundaries and duration.
3. **Security & Alerting (`security_monitor.py`)**
   - **Blacklisted App Detection:** Predefined list of tools (`wireshark`, `tcpdump`, `nmap`). 
   - **Suspicious Background Processes:** Configurable high CPU usage threshold alerting.
   - **Disk I/O Analysis:** Hooking into `psutil.disk_io_counters()` to measure exactly how much data is being written or read anomalously across processes.
   - **USB Insertion Tracking:** WMI on Windows, `/sys/bus/usb/devices` on Linux.
4. **Local Reporter (`local_reporter.py`)**
   - Serves an immediate local HTTP Basic authenticated dashboard with Chart.js analytics for offline analysis.
5. **API Sync Manager (`sync_manager.py`)**
   - Syncs payload to Django API endpoints `POST /api/logs/apps/` and `POST /api/logs/events/`.

---

## Next Actionable Verification Steps
- [x] Migrate Django models to support `Employee`, `IdleSession`, and `DailySummary`.
- [x] Refactor Django Views and Templates to build the 4 distinct Dashboard pages (Overview, Detail, Security, Analytics).
- [x] Implement Real-time AJAX polling for Device Detail audits (Screenshots, Commands, Security Events).

## 3. Real-time Audit Architecture
The system uses pure Vanilla JavaScript (Fetch API) to perform periodic polling (defaulting to 10s) of partial HTML fragments for the following components on the Device Detail page:
- **Screenshot Gallery**: Captures triggered by the "Visual Audit" command.
- **Command Trail**: History and status of remote commands (pending/executed/failed).
- **Security Timeline**: Real-time stream of security events and risk weightings.
