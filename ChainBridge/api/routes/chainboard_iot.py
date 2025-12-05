"""ChainSense IoT router exposing health summaries for ChainBoard."""

import os
from datetime import datetime

from fastapi import APIRouter

from api.chainsense.client import IoTDataProvider, MockIoTDataProvider
from api.schemas.chainboard import IoTHealthSummaryResponse

router = APIRouter(prefix="/chainboard/iot", tags=["chainboard-iot"])

# Environment toggle for IoT data source
USE_MOCK_IOT = os.getenv("CHAINBOARD_USE_MOCK_IOT", "true").lower() == "true"


def get_iot_provider() -> IoTDataProvider:
    """Get the configured IoT data provider."""
    if USE_MOCK_IOT:
        return MockIoTDataProvider()
    # Future: return RealIoTDataProvider() when connected to production platform
    return MockIoTDataProvider()


@router.get("/health", response_model=IoTHealthSummaryResponse)
async def get_iot_health() -> IoTHealthSummaryResponse:
    """Return the latest ChainSense IoT health snapshot."""

    provider = get_iot_provider()
    health_summary = provider.get_global_health()

    return IoTHealthSummaryResponse(
        iot_health=health_summary,
        generated_at=datetime.utcnow(),
    )
