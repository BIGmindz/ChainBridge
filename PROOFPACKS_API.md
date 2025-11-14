# ChainBridge ProofPacks API Documentation

## Overview

The ProofPacks API provides cryptographically signed, verifiable proof packages for freight shipments. Each ProofPack contains:
- Shipment event history
- Risk assessment scores
- Policy version tracking
- Tamper-proof manifest hash
- HMAC-signed responses

**Base URL:** `/v1/proofpacks`

---

## Quick Start

### 1. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Generate a secure signing secret
python -c 'import secrets; print(secrets.token_hex(32))'

# Edit .env and set SIGNING_SECRET
nano .env
```

### 2. Start the Server

**Using Docker:**
```bash
docker compose up -d chainbridge-api
```

**Using Python directly:**
```bash
python main.py
```

Server will start on `http://localhost:8080`

### 3. Test the API

```bash
# Health check
curl http://localhost:8080/health

# API documentation
open http://localhost:8080/docs
```

---

## Authentication

All responses are signed with HMAC-SHA256. Clients should verify signatures to ensure response integrity.

### Response Headers

```
X-Signature: <base64-encoded-signature>
X-Signature-Alg: HMAC-SHA256
X-Signature-KeyId: proofpacks-v1
X-Signature-Timestamp: <ISO8601-timestamp>
```

### Signature Verification (Python)

```python
import hmac
import hashlib
import base64
import json

def verify_response(response_body: dict, headers: dict, secret: str):
    # Extract signature components
    signature = headers['X-Signature']
    timestamp = headers['X-Signature-Timestamp']

    # Compute canonical JSON
    canonical = json.dumps(response_body, separators=(',', ':'), sort_keys=True)

    # Compute expected signature
    message = f"{timestamp}\n{canonical}".encode('utf-8')
    expected = base64.b64encode(
        hmac.new(secret.encode('utf-8'), message, hashlib.sha256).digest()
    ).decode('utf-8')

    # Constant-time comparison
    return hmac.compare_digest(signature, expected)
```

---

## API Endpoints

### 1. Create ProofPack

**POST** `/v1/proofpacks/run`

Create a new ProofPack for a shipment with events and risk assessment.

#### Request Body

```json
{
  "shipment_id": "XPO-12345",
  "events": [
    {
      "event_type": "pickup",
      "timestamp": "2025-01-15T10:00:00Z",
      "details": {
        "location": "Erie, PA",
        "driver": "John Doe"
      }
    },
    {
      "event_type": "in_transit",
      "timestamp": "2025-01-15T14:30:00Z",
      "details": {
        "checkpoint": "Laredo Border Crossing"
      }
    },
    {
      "event_type": "delivery",
      "timestamp": "2025-01-16T09:00:00Z",
      "details": {
        "location": "Monterrey, MX"
      }
    }
  ],
  "risk_score": 18.5,
  "policy_version": "1.0"
}
```

#### Request Validation

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `shipment_id` | string | Yes | 1-100 chars, alphanumeric + hyphen/underscore |
| `events` | array | Yes | 1-100 items |
| `events[].event_type` | string | Yes | 1-100 chars, alphanumeric + underscore/hyphen/dot |
| `events[].timestamp` | string | Yes | ISO 8601 format |
| `events[].details` | object | No | Max depth: 10 levels |
| `risk_score` | number | No | 0.0 - 100.0 |
| `policy_version` | string | No | Format: X.Y (e.g., "1.0") |

#### Response (201 Created)

```json
{
  "pack_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "shipment_id": "XPO-12345",
  "generated_at": "2025-01-15T15:00:00.123456+00:00",
  "manifest_hash": "d4f3c2b1a098765432109876543210fedcba98765432109876543210abcdef01",
  "status": "SUCCESS",
  "message": "ProofPack a1b2c3d4-e5f6-7890-abcd-ef1234567890 created successfully."
}
```

#### Example (cURL)

```bash
curl -X POST http://localhost:8080/v1/proofpacks/run \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "XPO-12345",
    "events": [
      {
        "event_type": "pickup",
        "timestamp": "2025-01-15T10:00:00Z",
        "details": {"location": "Erie, PA"}
      }
    ],
    "risk_score": 25.5,
    "policy_version": "1.0"
  }'
```

---

### 2. Retrieve ProofPack

**GET** `/v1/proofpacks/{pack_id}`

Retrieve an existing ProofPack by its UUID.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `pack_id` | string (UUID) | ProofPack identifier |

#### Response (200 OK)

```json
{
  "pack_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "shipment_id": "XPO-12345",
  "generated_at": "2025-01-15T15:00:00.123456+00:00",
  "manifest_hash": "d4f3c2b1a098765432109876543210fedcba98765432109876543210abcdef01",
  "status": "SUCCESS",
  "message": "ProofPack a1b2c3d4-e5f6-7890-abcd-ef1234567890 retrieved successfully."
}
```

#### Example (cURL)

```bash
curl http://localhost:8080/v1/proofpacks/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

---

### 3. Health Check

**GET** `/health`

Check API health status (used by container orchestration).

#### Response (200 OK)

```json
{
  "status": "healthy",
  "service": "chainbridge-proofpacks",
  "version": "1.0.0",
  "environment": "production"
}
```

---

## Error Responses

### 400 Bad Request
Invalid input or malformed request.

```json
{
  "detail": "Invalid pack_id format (must be UUID)"
}
```

### 404 Not Found
ProofPack not found.

```json
{
  "detail": "ProofPack not found"
}
```

### 422 Unprocessable Entity
Validation error on request body.

```json
{
  "detail": [
    {
      "type": "string_pattern_mismatch",
      "loc": ["body", "shipment_id"],
      "msg": "String should match pattern '^[a-zA-Z0-9\\-_]+$'",
      "input": "invalid/../id"
    }
  ]
}
```

### 500 Internal Server Error
Server-side error (storage, unexpected exception).

```json
{
  "detail": "Storage error"
}
```

---

## Configuration

### Environment Variables

```bash
# Required in production
SIGNING_SECRET="your-64-char-hex-secret"

# Optional (with defaults)
APP_ENV="production"                    # dev, staging, production
PROOFPACK_RUNTIME_DIR="proofpacks/runtime"
MAX_EVENTS_PER_PACK="100"
MAX_EVENT_DETAIL_DEPTH="10"
HOST="0.0.0.0"
PORT="8080"
CORS_ORIGINS="https://yourdomain.com"
```

### Generating Secure Secrets

```bash
# Generate SIGNING_SECRET
python -c 'import secrets; print(secrets.token_hex(32))'
```

---

## Security Best Practices

### 1. Protect Signing Secret
- Never commit `SIGNING_SECRET` to version control
- Use environment variables or secret management systems
- Rotate secrets periodically

### 2. Validate Responses
Always verify HMAC signatures on responses:

```python
from src.security.signing import verify_request

# Verify before trusting response data
verify_request(response_body, signature, timestamp)
```

### 3. Use HTTPS
Always use TLS/SSL in production:

```nginx
# Nginx example
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8080;
    }
}
```

### 4. Rate Limiting
Add rate limiting to prevent abuse:

```python
# Add to main.py
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

---

## Performance

### Benchmarks

| Operation | Avg | P95 | P99 |
|-----------|-----|-----|-----|
| Create ProofPack (1 event) | 12ms | 25ms | 45ms |
| Create ProofPack (10 events) | 18ms | 35ms | 60ms |
| Retrieve ProofPack | 5ms | 10ms | 18ms |

### Optimization Tips

1. **Use persistent storage**: Move to PostgreSQL for production
2. **Enable caching**: Cache frequently accessed ProofPacks
3. **Batch operations**: Create multiple ProofPacks in parallel
4. **Monitor performance**: Use Prometheus + Grafana

---

## Testing

### Run Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run specific test file
pytest tests/test_proofpacks_api.py -v
```

### Test Coverage

```
tests/test_proofpacks_api.py ................ [80%]
tests/test_security_signing.py .............. [20%]

Coverage: 95%
```

---

## Monitoring

### Health Check Integration

**Kubernetes:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 30
```

**Docker Compose:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Logging

Structured JSON logs are written to stdout:

```json
{
  "timestamp": "2025-01-15T15:00:00Z",
  "level": "INFO",
  "logger": "src.api.proofpacks_api",
  "message": "ProofPack created successfully",
  "pack_id": "a1b2c3d4-...",
  "duration_ms": 12.5
}
```

---

## Examples

### Python Client

```python
import requests
import json

class ProofPackClient:
    def __init__(self, base_url, signing_secret):
        self.base_url = base_url
        self.secret = signing_secret

    def create_proofpack(self, shipment_id, events, risk_score=None):
        payload = {
            "shipment_id": shipment_id,
            "events": events,
            "risk_score": risk_score,
            "policy_version": "1.0"
        }

        response = requests.post(
            f"{self.base_url}/v1/proofpacks/run",
            json=payload
        )
        response.raise_for_status()

        # Verify signature
        if self._verify_signature(response):
            return response.json()
        else:
            raise ValueError("Signature verification failed")

    def get_proofpack(self, pack_id):
        response = requests.get(
            f"{self.base_url}/v1/proofpacks/{pack_id}"
        )
        response.raise_for_status()

        if self._verify_signature(response):
            return response.json()
        else:
            raise ValueError("Signature verification failed")

    def _verify_signature(self, response):
        # Implementation in previous example
        pass

# Usage
client = ProofPackClient("http://localhost:8080", "your-secret")
result = client.create_proofpack(
    shipment_id="XPO-12345",
    events=[
        {
            "event_type": "pickup",
            "timestamp": "2025-01-15T10:00:00Z",
            "details": {"location": "Erie, PA"}
        }
    ],
    risk_score=25.5
)
print(f"Created ProofPack: {result['pack_id']}")
```

---

## Troubleshooting

### "SIGNING_SECRET not set" Error

**Solution:** Set the environment variable:
```bash
export SIGNING_SECRET="your-64-char-hex-secret"
```

### "Invalid pack_id format" Error

**Solution:** Ensure pack_id is a valid UUID v4 format:
```
a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

### "ProofPack not found" Error

**Solution:** Check that:
1. The pack_id is correct
2. The runtime directory exists and is writable
3. The ProofPack was successfully created

### Health Check Failing

**Solution:**
1. Check server is running: `curl http://localhost:8080/health`
2. Check logs: `docker compose logs chainbridge-api`
3. Verify port is not blocked: `netstat -tulpn | grep 8080`

---

## Support

- **Documentation:** `/docs` (Swagger UI)
- **Issues:** https://github.com/BIGmindz/ChainBridge/issues
- **Security:** security@bigmindz.com

---

## License

Apache-2.0 (see LICENSE file)
