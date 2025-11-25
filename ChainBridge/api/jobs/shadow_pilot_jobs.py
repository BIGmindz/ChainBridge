"""ARQ job for running and persisting Shadow Pilot simulations."""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict

from sqlalchemy.orm import Session, sessionmaker

from api.database import SessionLocal
from api.models.shadow_pilot import ShadowPilotRun, ShadowPilotShipment
from tools.shadow_pilot import run_shadow_pilot_from_csv

logger = logging.getLogger(__name__)


def _quantize_currency(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _to_int(value: float) -> int:
    try:
        return int(round(value))
    except Exception:
        return 0


def _get_session(ctx: Dict[str, Any]) -> Session:
    factory: sessionmaker = ctx.get("SessionLocal") or SessionLocal
    return factory()


async def run_shadow_pilot_job(
    ctx: Dict[str, Any],
    run_id: str,
    csv_path: str,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute the Shadow Pilot on a CSV and persist results.

    ctx may include a custom SessionLocal for testing; otherwise api.database.SessionLocal is used.
    """

    logger.info(
        "shadow_pilot.job.start",
        extra={"run_id": run_id, "csv_path": csv_path, "config": config},
    )
    summary, results, _ = run_shadow_pilot_from_csv(
        Path(csv_path),
        annual_rate=config["annual_rate"],
        advance_rate=config["advance_rate"],
        take_rate=config["take_rate"],
        min_value=config.get("min_value", 50000.0),
        min_truth=config.get("min_truth", 0.7),
        as_dataframe=False,
    )

    session = _get_session(ctx)
    try:
        run = session.query(ShadowPilotRun).filter(ShadowPilotRun.run_id == run_id).first()
        if run is None:
            run = ShadowPilotRun(
                run_id=run_id,
                prospect_name=config.get("prospect_name", "unknown"),
                period_months=int(config.get("period_months", 0)),
                input_filename=Path(csv_path).name,
                notes=config.get("notes"),
            )
            session.add(run)

        run.total_gmv_usd = _quantize_currency(summary.total_gmv_usd)
        run.financeable_gmv_usd = _quantize_currency(summary.financeable_gmv_usd)
        run.financed_gmv_usd = _quantize_currency(summary.financed_gmv_usd)
        run.protocol_revenue_usd = _quantize_currency(summary.protocol_revenue_usd)
        run.working_capital_saved_usd = _quantize_currency(summary.working_capital_saved_usd)
        run.losses_avoided_usd = _quantize_currency(summary.losses_avoided_usd)
        run.salvage_revenue_usd = _quantize_currency(summary.salvage_revenue_usd)
        run.average_days_pulled_forward = _quantize_currency(summary.average_days_pulled_forward)
        run.shipments_evaluated = int(summary.total_shipments)
        run.shipments_financeable = int(summary.financeable_shipments)
        run.updated_at = datetime.utcnow()

        session.query(ShadowPilotShipment).filter(ShadowPilotShipment.run_id == run_id).delete()
        shipment_rows = [
            ShadowPilotShipment(
                run_id=run_id,
                shipment_id=entry.shipment_id,
                corridor=getattr(entry, "corridor", None),
                mode=getattr(entry, "mode", None),
                customer_segment=getattr(entry, "customer_segment", None),
                cargo_value_usd=_quantize_currency(entry.cargo_value_usd),
                event_truth_score=Decimal(str(entry.event_truth_score)).quantize(Decimal("0.0001")),
                eligible_for_finance=bool(entry.financeable),
                financed_amount_usd=_quantize_currency(entry.financed_amount_usd),
                days_pulled_forward=_to_int(entry.days_pulled_forward),
                wc_saved_usd=_quantize_currency(entry.working_capital_saved_usd),
                protocol_revenue_usd=_quantize_currency(entry.protocol_revenue_usd),
                avoided_loss_usd=_quantize_currency(entry.avoided_loss_usd),
                salvage_revenue_usd=_quantize_currency(entry.salvage_revenue_usd),
                exception_flag=bool(entry.exception_flag),
                loss_flag=bool(entry.loss_flag),
            )
            for entry in results
        ]
        session.bulk_save_objects(shipment_rows)
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("shadow_pilot.job.failed", extra={"run_id": run_id})
        raise
    finally:
        session.close()

    logger.info(
        "shadow_pilot.job.complete",
        extra={
            "run_id": run_id,
            "shipments": len(results),
            "protocol_revenue_usd": float(summary.protocol_revenue_usd),
            "wc_saved_usd": float(summary.working_capital_saved_usd),
        },
    )
    return {"run_id": run_id, "shipments": len(results)}
