"""Read-only analytics helpers for ChainStake."""
from __future__ import annotations

import logging
from typing import Iterable, List

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from api.models.chainstake import StakePosition
from api.models.chainpay import PaymentIntent
from api.schemas.chainstake import LiquidityOverview, StakePoolSummary, StakePositionRead

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = {"QUEUED", "MINTING", "STAKING_IN_POOL", "LIQUIDITY_SENT"}
UTILIZED_STATUSES = {"STAKING_IN_POOL", "LIQUIDITY_SENT"}
TVL_STATUSES = {"STAKING_IN_POOL", "LIQUIDITY_SENT", "CLOSED"}

RISK_SCORE = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
RISK_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def _avg_risk_from_scores(scores: Iterable[int]) -> str:
    scores = list(scores)
    if not scores:
        return "LOW"
    avg = sum(scores) / len(scores)
    idx = min(len(RISK_LEVELS) - 1, int(round(avg - 1)))
    return RISK_LEVELS[idx]


def _weighted_avg(values: Iterable[tuple[float, float]]) -> float:
    total_weight = 0.0
    acc = 0.0
    for value, weight in values:
        if weight is None or value is None:
            continue
        acc += value * weight
        total_weight += weight
    return acc / total_weight if total_weight else 0.0


def get_liquidity_overview(session: Session) -> LiquidityOverview:
    tvl = (
        session.query(func.coalesce(func.sum(StakePosition.notional_usd), 0.0))
        .filter(StakePosition.status.in_(TVL_STATUSES))
        .scalar()
    )
    utilized = (
        session.query(func.coalesce(func.sum(StakePosition.notional_usd), 0.0))
        .filter(StakePosition.status.in_(UTILIZED_STATUSES))
        .scalar()
    )
    active_positions = (
        session.query(func.count(StakePosition.id))
        .filter(~StakePosition.status.in_(["FAILED", "CLOSED"]))
        .scalar()
    )
    apy_rows = (
        session.query(StakePosition.realized_apy, StakePosition.notional_usd)
        .filter(StakePosition.realized_apy.isnot(None))
        .all()
    )
    overall_apy = _weighted_avg((row[0], row[1]) for row in apy_rows)

    logger.info(
        "chainstake_liquidity_overview",
        extra={
            "total_tvl_usd": tvl,
            "total_utilized_usd": utilized,
            "active_positions": active_positions,
        },
    )
    return LiquidityOverview(
        total_tvl_usd=float(tvl or 0.0),
        total_utilized_usd=float(utilized or 0.0),
        overall_realized_apy=float(overall_apy),
        active_positions=int(active_positions or 0),
    )


def list_stake_pools(session: Session) -> List[StakePoolSummary]:
    pool_rows = (
        session.query(
            StakePosition.pool_id,
            func.coalesce(func.sum(StakePosition.notional_usd), 0.0).label("tvl"),
            func.coalesce(
                func.sum(
                    case((StakePosition.status.in_(UTILIZED_STATUSES), StakePosition.notional_usd), else_=0.0)
                ),
                0.0,
            ).label("utilized"),
            func.count(StakePosition.id).label("total_positions"),
            func.coalesce(
                func.sum(
                    case((StakePosition.status == "FAILED", 1), else_=0)
                ),
                0,
            ).label("defaulted"),
        )
        .group_by(StakePosition.pool_id)
        .all()
    )

    summaries: List[StakePoolSummary] = []
    for row in pool_rows:
        pool_id = row[0]
        tvl_usd = float(row[1] or 0.0)
        utilized_usd = float(row[2] or 0.0)
        total_positions = int(row[3] or 0)
        defaulted = int(row[4] or 0)

        risk_scores = [
            RISK_SCORE.get(risk, 1)
            for (risk,) in session.query(StakePosition.risk_level).filter(StakePosition.pool_id == pool_id).all()
            if risk
        ]
        avg_risk = _avg_risk_from_scores(risk_scores)

        apy_rows = (
            session.query(StakePosition.realized_apy, StakePosition.notional_usd)
            .filter(StakePosition.pool_id == pool_id, StakePosition.realized_apy.isnot(None))
            .all()
        )
        realized_apy = _weighted_avg((r[0], r[1]) for r in apy_rows)

        open_positions = (
            session.query(func.count(StakePosition.id))
            .filter(StakePosition.pool_id == pool_id)
            .filter(StakePosition.status != "CLOSED")
            .scalar()
        )

        default_rate_bps = 0.0
        if total_positions:
            default_rate_bps = (defaulted / total_positions) * 10000

        summaries.append(
            StakePoolSummary(
                pool_id=pool_id,
                label=f"Pool {pool_id}",
                corridor="GLOBAL",
                tenor_days=30,
                transport_mode="OCEAN",
                tvl_usd=tvl_usd,
                utilized_usd=utilized_usd,
                target_tvl_usd=round(tvl_usd * 1.2, 2),
                base_apy=8.5,
                realized_apy=realized_apy,
                avg_risk_level=avg_risk,  # type: ignore
                open_positions=int(open_positions or 0),
                default_rate_bps=round(default_rate_bps, 2),
            )
        )
    logger.info("chainstake_pools_listed", extra={"pools": len(summaries)})
    return summaries


def list_pool_positions(session: Session, pool_id: str) -> List[StakePositionRead]:
    positions = (
        session.query(StakePosition)
        .filter(StakePosition.pool_id == pool_id)
        .order_by(StakePosition.staked_at.desc())
        .all()
    )
    if positions is None:
        return []

    pi_lookup = {
        pi.id: pi
        for pi in session.query(PaymentIntent).filter(
            PaymentIntent.id.in_([p.payment_intent_id for p in positions if p.payment_intent_id])
        )
    }

    def _serialize(pos: StakePosition) -> StakePositionRead:
        pi = pi_lookup.get(pos.payment_intent_id)
        payout_conf = pos.payout_confidence if pos.payout_confidence is not None else (pi.payout_confidence if pi else None)
        final_payout = pos.final_payout_amount if pos.final_payout_amount is not None else (pi.final_payout_amount if pi else None)
        risk = pos.risk_level or "LOW"
        return StakePositionRead(
            position_id=pos.id,
            shipment_id=pos.shipment_id,
            payment_intent_id=pos.payment_intent_id,
            pool_id=pos.pool_id,
            corridor=pos.corridor or "GLOBAL",
            notional_usd=pos.notional_usd or 0.0,
            staked_at=pos.staked_at,
            expected_maturity_at=pos.expected_maturity_at,
            realized_apy=pos.realized_apy,
            stake_status=pos.status,
            risk_level=risk,  # type: ignore
            payout_confidence=payout_conf,
            final_payout_amount=final_payout,
        )

    return [_serialize(p) for p in positions]
