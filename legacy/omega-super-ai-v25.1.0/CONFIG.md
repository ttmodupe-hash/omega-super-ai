# Luqi AI v24.5.0 — Configuration Guide
## Autonomous Multi-Agent System Setup

---

### Quick Start (No Configuration Needed)

The system works out of the box. All alerts are logged to `data/alerts.jsonl`.

```powershell
cd C:\Users\LUQMA\omega-super-ai
py -3.11 -m uvicorn backend.router:app --reload
```

---

### Optional: Discord Alert Notifications

1. Open Discord → Server Settings → Integrations → Webhooks
2. Click "New Webhook" → Choose channel → Copy URL
3. Set environment variable before starting server:

```powershell
$env:DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/123456789/abcdef..."
py -3.11 -m uvicorn backend.router:app --reload
```

---

### Optional: Slack Alert Notifications

1. Open Slack → Apps → Incoming Webhooks → Add to Slack
2. Choose channel → Copy Webhook URL
3. Set environment variable:

```powershell
$env:SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/T00/B00/XXXX"
py -3.11 -m uvicorn backend.router:app --reload
```

---

### Optional: Custom Alert Log Path

```powershell
$env:ALERT_LOG_PATH = "C:\Users\LUQMA\omega-super-ai\data\alerts.jsonl"
```

---

### System Mode Toggle

Default: **Human-in-the-Loop** (safe — you approve all updates)

To enable Fully Autonomous mode (deploys after tests pass):
```powershell
# Set before starting server
$env:AUTO_DEPLOY = "true"
```

Or via API after server is running:
```bash
curl -X POST http://localhost:8000/api/system/config \
  -H "Content-Type: application/json" \
  -d '{"mode": "fully_autonomous", "auto_deploy": true}'
```

---

### Available Endpoints (New in v24.5.0)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/system/status` | GET | Full system status |
| `/api/system/health-check` | POST | Trigger health check |
| `/api/system/alerts` | GET | Active alerts |
| `/api/system/alerts/ack` | POST | Acknowledge alert |
| `/api/system/research` | GET | Research findings |
| `/api/system/research/run` | POST | Run research cycle |
| `/api/system/updates` | GET | Update queue |
| `/api/system/validate` | POST | Validate code |
| `/api/system/approve-deploy/{id}` | POST | Approve & deploy |
| `/api/system/rollback` | POST | Emergency rollback |
| `/api/system/config` | GET/POST | System configuration |

---

### Testing

```powershell
# Run startup verification
py test_v25.py

# Check system status (server must be running)
curl http://localhost:8000/api/system/status

# Check health
curl http://localhost:8000/api/system/health-check

# View active alerts
curl http://localhost:8000/api/system/alerts

# Trigger research cycle
curl -X POST http://localhost:8000/api/system/research/run
```
