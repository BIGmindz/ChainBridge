# FRONTEND_SONNY – Quick-Start Checklist

1. Locate the ChainBoard UI project (e.g., `chainboard-ui/`) in the repo.
2. Identify current pages/sections for:
   - Control Tower
   - Intelligence / Risk
   - Settlements
   - IoT / ChainSense
3. Review any existing API client or fetch layer used by the frontend.
4. Document (or confirm) the current endpoints used by ChainBoard for:
   - Shipments
   - Risk scores
   - Settlements
   - IoT status
5. Implement or refine a small, non-critical UI component first:
   - For example, a simple "IoT Health Summary" or "Risk Banner" widget.
6. Add proper TypeScript types for the payload returned by that endpoint.
7. Handle loading, success, empty, and error states explicitly for that component.
8. Coordinate with Cody if the current API shapes are unclear or inconsistent.
9. Add a basic test (unit or integration) for at least one key component or hook.
10. Capture a screenshot or short UX summary to share with Benson/Product for review.
