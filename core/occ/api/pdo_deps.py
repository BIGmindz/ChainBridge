"""FastAPI dependencies for PDO gate enforcement on OCC write paths.

All OCC write operations (create, update, delete) MUST use these dependencies
to ensure "No PDO → No execution" is enforced at the API layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from fastapi import Header, HTTPException

if TYPE_CHECKING:
    pass


class OCCWriteGate:
    """
    FastAPI dependency that enforces PDO gate on OCC write operations.

    Usage in endpoint:
        @router.post("", dependencies=[Depends(require_pdo_header)])
        async def create_something(...):
            ...

    Or inject the PDO:
        @router.post("")
        async def create_something(
            pdo: GatewayPDO = Depends(get_pdo_from_header),
        ):
            ...
    """

    @staticmethod
    def _extract_pdo_id(header_value: Optional[str]) -> Optional[str]:
        """Extract PDO ID from header value."""
        if not header_value:
            return None
        # Header format: "PDO <pdo_id>" or just "<pdo_id>"
        if header_value.startswith("PDO "):
            return header_value[4:].strip()
        return header_value.strip()


async def require_pdo_header(
    x_pdo_id: Optional[str] = Header(None, alias="X-PDO-ID"),
    x_pdo_approved: Optional[str] = Header(None, alias="X-PDO-Approved"),
) -> None:
    """
    FastAPI dependency that blocks requests without a valid PDO header.

    For OCC write operations, callers must provide:
    - X-PDO-ID: The PDO correlation ID
    - X-PDO-Approved: Must be "true" (string)

    This is a lightweight header-based gate. For full PDO validation,
    use the gateway's DecisionEngine.execute() method.

    Raises:
        HTTPException 403: If PDO headers are missing or invalid.
    """
    if not x_pdo_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "PDO_REQUIRED",
                "message": "OCC write operations require X-PDO-ID header",
            },
        )

    if x_pdo_approved != "true":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "PDO_NOT_APPROVED",
                "message": "OCC write operations require X-PDO-Approved: true header",
                "pdo_id": x_pdo_id,
            },
        )


async def optional_pdo_header(
    x_pdo_id: Optional[str] = Header(None, alias="X-PDO-ID"),
    x_pdo_approved: Optional[str] = Header(None, alias="X-PDO-Approved"),
) -> Optional[str]:
    """
    FastAPI dependency that extracts PDO ID if present but doesn't require it.

    Use this for read operations that optionally track PDO context.

    Returns:
        The PDO ID if headers are valid, None otherwise.
    """
    if x_pdo_id and x_pdo_approved == "true":
        return x_pdo_id
    return None
