# BACKEND_CODY – Quick-Start Checklist

1. Review `/chainpay-service/app/api.py` and identify core endpoints.
2. Inspect the existing canonical models and ensure naming is consistent.
3. Implement or refine:
   - Shipment model
   - Milestone event types
   - Settlement state machine logic
4. Create or update Pydantic schemas for:
   - Requests
   - Responses
   - Error message formats
5. Add structured logging for all endpoints.
6. Add idempotency keys or deterministic logic for repeated events.
7. Implement or refine SSE channels for:
   - Shipment updates
   - IoT status changes
   - Settlement progress
8. Add a test suite for:
   - ProofPack building
   - Milestone-based settlement execution
   - API response validation
9. Document new endpoints in `/docs/api/chainpay.md`.
10. Sync with Sonny to validate payload shapes for UI consumption.
