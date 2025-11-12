# ChainFreight + ChainIQ Integration - Quick Summary

## What Changed

### 1. Database Models (app/models.py)

Added 3 new fields to `FreightToken`:

```text
- risk_score      (Float, nullable)
- risk_category   (String, nullable)  
- recommended_action (String, nullable)
```

### 2. API Schemas (app/schemas.py)

Updated `FreightTokenResponse` to include:

```text
- risk_score: Optional[float] (0.0-1.0)
- risk_category: Optional[str]
- recommended_action: Optional[str]
```

### 3. ChainIQ Client (app/chainiq_client.py) - NEW FILE

Created async HTTP client to call ChainIQ scoring service:

**Main function:**
- `score_shipment()` - Calls `/score/shipment` endpoint, returns risk tuple or None

**Features:**
- 10-second timeout
- Graceful error handling if ChainIQ unavailable
- Auto-generates recommended_action based on risk level
- Logs all scoring calls and errors

### 4. Tokenization Endpoint (app/main.py)

Updated `POST /shipments/{id}/tokenize` to:

1. Look up shipment details (origin, destination, dates)
2. Call ChainIQ scoring automatically
3. Store risk_score, risk_category, recommended_action in token
4. Continue if ChainIQ unavailable (risk fields set to null)

## Workflow

``` bash
User: POST /shipments/1/tokenize
  │
  ├─> ChainFreight validates shipment exists
  │
  ├─> ChainFreight calls ChainIQ (async)
  │   │
  │   └─> ChainIQ returns risk_score, risk_category, confidence
  │
  ├─> ChainFreight generates recommended_action
  │
  └─> Token created and returned with all risk fields

Result:
{
  "id": 1,
  "shipment_id": 1,
  "face_value": 100000.00,
  "currency": "USD",
  "status": "created",
  "risk_score": 0.35,
  "risk_category": "low",
  "recommended_action": "APPROVE - Low risk",
  ...
}
```

## Recommended Actions

| Risk | Score | Action |
|------|-------|--------|
| LOW | 0.0-0.33 | APPROVE |
| MEDIUM | 0.33-0.67 | APPROVE_WITH_CONDITIONS / REVIEW |
| HIGH | 0.67-1.0 | REVIEW_URGENTLY / REJECT |

## Error Handling

**If ChainIQ service is down:**
- Tokenization STILL SUCCEEDS
- Risk fields set to NULL
- Warning logged
- User can query risk later when service recovers

**If ChainIQ service times out (>10s):**
- Tokenization STILL SUCCEEDS
- Risk fields set to NULL
- Warning logged

## Testing

### Start both services:

```bash
# Terminal 1: ChainIQ
cd chainiq-service
python -m uvicorn app.main:app --port 8001 --reload

# Terminal 2: ChainFreight
cd chainfreight-service
python -m uvicorn app.main:app --port 8002 --reload
```

### Test tokenization:

```bash
# 1. Create shipment
curl -X POST "http://localhost:8002/shipments" \
  -H "Content-Type: application/json" \
  -d '{"shipper_name":"Test","origin":"LA","destination":"CHI","cargo_value":100000}'

# 2. Tokenize (auto-scores via ChainIQ)
curl -X POST "http://localhost:8002/shipments/1/tokenize" \
  -H "Content-Type: application/json" \
  -d '{"face_value":100000,"currency":"USD"}'

# 3. Check token has risk fields
curl "http://localhost:8002/tokens/1"
```

## Code Status

✅ **All files error-free:**
- models.py - Compiles ✅
- schemas.py - Compiles ✅
- main.py - Compiles ✅
- chainiq_client.py - Compiles ✅

## Files Modified

- `app/models.py` - Added risk fields to FreightToken
- `app/schemas.py` - Updated FreightTokenResponse schema
- `app/main.py` - Integrated ChainIQ scoring in tokenize endpoint

## Files Created

- `app/chainiq_client.py` - ChainIQ HTTP client
- `CHAINIQ_INTEGRATION.md` - Full integration guide
- `CHAINIQ_INTEGRATION_SUMMARY.md` - This file

## Next Steps (Optional)

1. Run local tests to verify integration
2. Update database migration if deploying to prod
3. Configure CHAINIQ_URL environment variable
4. Set up monitoring for scoring failures
5. Future: Async job queue (Celery) for non-blocking scoring

---

**Status**: ✅ Ready to test
**Date**: November 7, 2025
