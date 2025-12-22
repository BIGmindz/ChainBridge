# api/routes/agents.py
"""
FastAPI Router for Agent Framework Management

Provides programmatic access to ChainBridge Agent Framework validation
and status information. Designed for operational dashboards and health checks.

Router Design:
- **Prefix**: Routes use `/api/agents` prefix (configured in server.py)
- **Tags**: Grouped under "Agent Framework" in OpenAPI docs
- **Data Source**: Backed by tools.agent_validate.get_validation_results()
- **Security**: Stateless, read-only operations

Author: ChainBridge Platform Team
Version: 1.0.0 (Production-Ready)
"""

import logging

from fastapi import APIRouter

from api.schemas.agent_status import AgentStatusResponse
from tools.agent_validate import get_validation_results

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/agents",
    tags=["Agent Framework"],
)


@router.get("/status", response_model=AgentStatusResponse)
async def get_agents_status() -> AgentStatusResponse:
    """
    Retrieve current validation status for all agents in the framework.

    This endpoint provides real-time insight into agent framework health,
    including total agent count, valid/invalid counts, and specific role
    names for agents requiring attention.

    **Use Cases:**
    - Operational dashboards displaying agent health
    - CI/CD health checks before deployment
    - Monitoring systems tracking framework stability
    - Executive reporting on platform readiness

    **Returns:**
    - `total`: Total number of agents in AGENTS directory
    - `valid`: Number of agents passing all validation checks
    - `invalid`: Number of incomplete/invalid agents (total - valid)
    - `invalid_roles`: Specific role names needing remediation

    **Example Response:**
    ```json
    {
      "total": 20,
      "valid": 17,
      "invalid": 3,
      "invalid_roles": [
        "AI_AGENT_TIM",
        "AI_RESEARCH_BENSON",
        "BIZDEV_PARTNERSHIPS_LEAD"
      ]
    }
    ```
    """
    logger.debug("Fetching agent validation status")

    # Call shared validation logic from agent_validate
    valid_count, total_count, invalid_roles = get_validation_results()

    # Calculate invalid count (mathematical consistency check)
    invalid_count = total_count - valid_count

    logger.debug(
        "Agent status: %d/%d valid (%d invalid)",
        valid_count,
        total_count,
        invalid_count,
    )

    return AgentStatusResponse(
        total=total_count,
        valid=valid_count,
        invalid=invalid_count,
        invalid_roles=invalid_roles,
    )
