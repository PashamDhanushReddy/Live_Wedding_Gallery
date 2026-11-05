# Production Observability, Monitoring & Failure Runbook
**Live Wedding Gallery Infrastructure & Operations Guide**

See the complete operational guide in the project artifact or review the quick summary below.

## Quick Diagnostic Commands

```powershell
# 1. Full Backend & Observability Automated Test Suite (65 Tests)
$env:PYTHONPATH="backend"
python -m unittest photos.tests weddings.tests faces.tests photos.test_queue photos.test_security weddings.test_capacity test_integration_lifecycle observability.tests

# 2. Django Configuration & Model Sanity Check
python backend/manage.py check

# 3. Live Observability Dashboard Snapshot
curl -s "http://localhost:8000/api/observability/dashboard/" | jq .summary

# 4. End-to-End Photo Tracing Verification
curl -s "http://localhost:8000/api/observability/trace/?id=ceremony_kiss.jpg" | jq .milestones
```

## Production Observability Endpoints
- **Live Observability UI:** `/admin/live`
- **Dashboard JSON:** `GET /api/observability/dashboard/`
- **Raw Metrics:** `GET /api/observability/metrics/`
- **Active Alerts:** `GET /api/observability/alerts/`
- **Photo Tracer:** `GET /api/observability/trace/?id=<ID>`
- **Retry Dead-Letters:** `POST /api/observability/jobs/retry-dead-letters/`

