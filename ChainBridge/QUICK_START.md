# Quick Start Guide for ChainBridge Platform

Get all ChainBridge services running in minutes!

## Prerequisites

- Python 3.11+
- pip
- Virtual environment manager (venv or conda)

## 1. Clone and Navigate

```bash
cd /path/to/ChainBridge
```

## 2. Start Each Service

Open three terminal windows (or use a terminal multiplexer like tmux):

### Terminal 1: ChainBoard (Driver Service)

```bash
cd chainboard-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Output**: Service starts at `http://localhost:8000`

### Terminal 2: ChainFreight (Shipment Service)

```bash
cd chainfreight-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
```

**Output**: Service starts at `http://localhost:8002`

### Terminal 3: ChainIQ (ML Scoring Service)

```bash
cd chainiq-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

**Output**: Service starts at `http://localhost:8001`

## 3. Verify Services Are Running

```bash
# Check health endpoints
curl http://localhost:8000/health
curl http://localhost:8002/health
curl http://localhost:8001/health

# Expected: {"status":"ok","service":"chainboard"} (or similar)
```

## 4. Access API Documentation

Open in your browser:

- [ChainBoard](http://localhost:8000/docs)
- [ChainFreight](http://localhost:8002/docs)
- [ChainIQ](http://localhost:8001/docs)

## 5. Test with Example Workflow

### 5a. Create a Driver

```bash
curl -X POST "http://localhost:8000/drivers" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Alice",
    "last_name": "Smith",
    "email": "alice@shipping.com",
    "phone": "555-1234",
    "dot_number": "DOT123456",
    "cdl_number": "CDL789012"
  }'
```

**Response** (example):

```json
{
  "id": 1,
  "first_name": "Alice",
  "last_name": "Smith",
  "email": "alice@shipping.com",
  "phone": "555-1234",
  "dot_number": "DOT123456",
  "cdl_number": "CDL789012",
  "is_active": true,
  "created_at": "2025-11-07T10:00:00",
  "updated_at": "2025-11-07T10:00:00"
}
```

Save the `id` for next step.

### 5b. Create a Shipment

```bash
curl -X POST "http://localhost:8002/shipments" \
  -H "Content-Type: application/json" \
  -d '{
    "shipper_name": "ACME Corp",
    "origin": "Los Angeles, CA",
    "destination": "Chicago, IL",
    "pickup_date": "2025-11-08T08:00:00",
    "planned_delivery_date": "2025-11-15T12:00:00"
  }'
```

**Response** (example):

```json
{
  "id": 1,
  "shipper_name": "ACME Corp",
  "origin": "Los Angeles, CA",
  "destination": "Chicago, IL",
  "pickup_date": "2025-11-08T08:00:00",
  "planned_delivery_date": "2025-11-15T12:00:00",
  "status": "pending",
  "actual_delivery_date": null,
  "created_at": "2025-11-07T10:01:00",
  "updated_at": "2025-11-07T10:01:00"
}
```

Save the `id` for next step.

### 5c. Score the Shipment

```bash
curl -X POST "http://localhost:8001/score/shipment" \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "1",
    "driver_id": 1,
    "origin": "Los Angeles, CA",
    "destination": "Chicago, IL",
    "planned_delivery_date": "2025-11-15T12:00:00"
  }'
```

**Response** (example):

```json
{
  "shipment_id": "1",
  "risk_score": 0.42,
  "risk_category": "medium",
  "confidence": 0.60,
  "reasoning": "Placeholder scoring - waiting for ML engine integration"
}
```

### 5d. Update Shipment Status

```bash
# Pick up the shipment
curl -X PUT "http://localhost:8002/shipments/1" \
  -H "Content-Type: application/json" \
  -d '{"status": "picked_up"}'

# Move to in transit
curl -X PUT "http://localhost:8002/shipments/1" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_transit"}'

# Mark as delivered
curl -X PUT "http://localhost:8002/shipments/1" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "delivered",
    "actual_delivery_date": "2025-11-14T14:30:00"
  }'
```

## 6. Next Steps

### Explore APIs

Each service has interactive Swagger documentation at the `/docs` endpoint. Try different endpoints and see live responses.

### Use Copilot for Development

See `COPILOT_CONTEXT.md` for guidance on using GitHub Copilot to extend these services.

### Read Architecture

See `ARCHITECTURE.md` for detailed information about service communication patterns and integration.

### Stop Services

When done, stop each service:

```bash
# In each terminal, press Ctrl+C
```

## Common Commands

### List All Drivers

```bash
curl "http://localhost:8000/drivers"
```

### List All Shipments

```bash
curl "http://localhost:8002/shipments"
```

### Search Drivers by Email

```bash
curl "http://localhost:8000/drivers/search?email=alice@shipping.com"
```

### List Only In-Transit Shipments

```bash
curl "http://localhost:8002/shipments?status=in_transit"
```

## Troubleshooting

### Port Already in Use

If you get "Port 8000 already in use", another service is using that port.

```bash
# Check what's using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process (macOS/Linux)
kill -9 <PID>
```

Or use different ports:

```bash
uvicorn app.main:app --port 8010  # Use 8010 instead
```

### Database Errors

If you see database errors, reset the databases:

```bash
# In project root
rm chainboard-service/chainboard.db
rm chainfreight-service/chainfreight.db

# Restart services - they auto-create on startup
```

### Dependency Installation Errors

Make sure you're using Python 3.11+:

```bash
python --version  # Should be 3.11+
```

If issues persist:

```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

## Next: Extend with Copilot

Now that services are running, you can use GitHub Copilot Chat to extend them:

1. Open VS Code
2. Open Copilot Chat (Ctrl+Shift+I)
3. Paste the **Global Copilot Context** from `COPILOT_CONTEXT.md`
4. Ask Copilot to help build new features

Example:

> "Create a new endpoint in ChainBoard to list drivers by name. Use fuzzy matching."

See `COPILOT_CONTEXT.md` for more ready-to-use prompts!

## Files Reference

| File | Purpose |
|------|---------|
| `COPILOT_CONTEXT.md` | Guidance for GitHub Copilot |
| `ARCHITECTURE.md` | Detailed architecture overview |
| `chainboard-service/README.md` | ChainBoard service docs |
| `chainfreight-service/README.md` | ChainFreight service docs |
| `chainiq-service/README.md` | ChainIQ service docs |

## Support

For questions or issues:

1. Check the relevant service `README.md`
2. Review `ARCHITECTURE.md` for integration patterns
3. Check `COPILOT_CONTEXT.md` for development guidance

Happy building! 🚀
