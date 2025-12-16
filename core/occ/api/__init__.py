"""OCC API routers."""

from core.occ.api.artifacts import router as artifacts_router
from core.occ.api.audit_events import router as audit_events_router

__all__ = ["artifacts_router", "audit_events_router"]
