# API Reference - Project RAT

This document details the communication protocol between the `rat_agent` and the `rat_web` server. All endpoints are relative to the `SERVER_URL`.

## 1. Agent Registration
**Endpoint**: `POST /api/agents/register/`

Allows a new agent to register itself or an existing agent to update its status.

### Request Body
```json
{
  "machine_id": "WS-DEVELOPER-01",
  "os_name": "Windows",
  "ip_address": "192.168.1.45"
}
```

### Success Response (`201 Created` or `200 OK`)
```json
{
  "agent_id": 1,
  "data": {
    "id": 1,
    "machine_id": "WS-DEVELOPER-01",
    "os_name": "Windows",
    "ip_address": "192.168.1.45",
    "is_online": true
  }
}
```

---

## 2. Push Application Logs
**Endpoint**: `POST /api/logs/apps/`

Synchronizes application session data from the agent's local cache.

### Request Body
```json
{
  "agent_id": "1",
  "logs": [
    {
      "app_name": "Visual Studio Code",
      "start_time": "2024-04-10T10:00:00Z",
      "end_time": "2024-04-10T10:15:00Z",
      "duration_seconds": 900,
      "data_rx_bytes": 50000,
      "data_tx_bytes": 12000,
      "disk_read_bytes": 1000,
      "disk_write_bytes": 500
    }
  ]
}
```

### Success Response (`201 Created`)
```json
{
  "status": "success",
  "inserted": 1
}
```

---

## 3. Push Event Logs
**Endpoint**: `POST /api/logs/events/`

Synchronizes security events and idle periods.

### Request Body
```json
{
  "agent_id": "1",
  "logs": [
    {
      "event_type": "usb_insertion",
      "description": "New USB Device: Kingston DataTraveler",
      "timestamp": "2024-04-10T10:20:00Z"
    },
    {
      "event_type": "idle",
      "duration": 300,
      "timestamp": "2024-04-10T10:25:00Z"
    }
  ]
}
```

### Success Response (`201 Created`)
```json
{
  "status": "success",
  "inserted": 2
}
```
> [!NOTE]
> `idle` events are automatically parsed by the server and stored in the `IdleSession` model instead of `SecurityEvent`.

---

## 4. Performance & Scaling

To handle high volumes of telemetry data, the following constraints and optimizations are applied:

- **Batch Size**: The `SyncManager` enforces a limit of **1,000 logs per chunk** to prevent request timeouts and server-side memory pressure.
- **Concurrency**: The agent uses a pool of **3 parallel workers** for API synchronization, allowing it to clear large backlogs across multiple HTTP connections.
- **Bulk Operations**: The server-side code is optimized for bulk data ingestion using Django's `bulk_create` where appropriate (e.g., software inventory).

