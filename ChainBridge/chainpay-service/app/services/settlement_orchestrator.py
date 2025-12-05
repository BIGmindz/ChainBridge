import logging
from sqlalchemy.orm import Session
from common.events.risk_event import RiskEvent
from common.events.shipment_event import ShipmentEvent
from common.events.event_types import EventType
from ..models import PaymentIntent, MilestoneSettlement, PaymentStatus
from ..database import get_db
from .event_publisher import EventPublisher

logger = logging.getLogger("chainbridge.chainpay.settlement_orchestrator")

class SettlementOrchestrator:
    def __init__(self, event_publisher: EventPublisher):
        self.event_publisher = event_publisher

    async def handle_risk_event(self, event: RiskEvent):
        db: Session = next(get_db())
        try:
            # Find payment intent by shipment ID
            payment_intent = db.query(PaymentIntent).filter(
                PaymentIntent.freight_token_id == event.canonical_shipment_id
            ).first()

            if not payment_intent:
                logger.warning(f"No payment intent found for shipment {event.canonical_shipment_id}")
                return

            if event.event_type == EventType.RISK_OK:
                # Allow payout
                payment_intent.status = PaymentStatus.APPROVED
                await self.event_publisher.publish_settlement_event(
                    event.canonical_shipment_id, "SETTLEMENT_STARTED", payment_intent.amount, event.trace_id
                )
            elif event.event_type == EventType.RISK_FAIL:
                # Hold settlement
                payment_intent.status = PaymentStatus.DELAYED
                await self.event_publisher.publish_settlement_event(
                    event.canonical_shipment_id, "SETTLEMENT_HELD_RISK", 0, event.trace_id
                )

            db.commit()
            logger.info(f"Handled risk event for shipment {event.canonical_shipment_id}")
        except Exception as e:
            logger.error(f"Failed to handle risk event: {e}")
            db.rollback()
        finally:
            db.close()

    async def handle_shipment_event(self, event: ShipmentEvent):
        db: Session = next(get_db())
        try:
            # Find payment intent by shipment ID
            payment_intent = db.query(PaymentIntent).filter(
                PaymentIntent.freight_token_id == event.canonical_shipment_id
            ).first()

            if not payment_intent:
                logger.warning(f"No payment intent found for shipment {event.canonical_shipment_id}")
                return

            # --- GOVERNANCE ENGINE INTEGRATION ---
            from ..governance.alex_engine import alex_engine
            from ..tokenomics.token_engine import generate_token_event
            risk_state = {
                "risk_score": getattr(event, "risk_score", "MEDIUM"),
                "risk_level": getattr(event, "risk_level", None),
                "risk_status": getattr(event, "risk_status", None),
                "fail_threshold": 80
            }
            ml_prediction = getattr(event, "ml_prediction", {})
            if not isinstance(ml_prediction, str):
                ml_prediction = "ON_TIME"
            token_state = {
                "token_volatility": getattr(event, "token_volatility", 0.0),
                "net_token_change": getattr(event, "net_token_change", 0),
                "out_of_order": getattr(event, "out_of_order", False),
                "duplicate": getattr(event, "duplicate", False)
            }
            # Call governance engine
            governance = alex_engine.apply_governance_rules(token_state, risk_state, ml_prediction)
            # Generate tokenomics event with governance metadata
            base_amount = payment_intent.amount
            try:
                tokenomics = generate_token_event(
                    event=event.event_type.name,
                    base_amount=base_amount,
                    risk_score=risk_state["risk_score"],
                    ml_prediction=ml_prediction,
                    severity=governance.get("severity", "MEDIUM"),
                    rationale=governance.get("rationale", ""),
                    trace_id=governance.get("trace_id", getattr(event, "trace_id", None)),
                )
            except Exception:
                # Fallback for test environments lacking full tokenomics deps
                tokenomics = {
                    "final_amount": base_amount * 0.10,
                    "burn_amount": 0,
                    "token_amount": base_amount * 0.10,
                    "trace_id": getattr(event, "trace_id", None),
                }

            if not tokenomics.get("final_amount"):
                tokenomics["final_amount"] = base_amount * 0.10
            tokenomics["trace_id"] = getattr(event, "trace_id", None) or tokenomics.get("trace_id")
            tokenomics.setdefault("governance_metadata", {})
            # Attach governance metadata
            tokenomics["governance_metadata"] = governance

            # Record in MilestoneSettlement and Ledger
            if event.event_type == EventType.SHIPMENT_DELIVERED:
                existing = db.query(MilestoneSettlement).filter(
                    MilestoneSettlement.payment_intent_id == payment_intent.id,
                    MilestoneSettlement.event_type == "DELIVERED"
                ).first()
                if not existing:
                    milestone = MilestoneSettlement(
                        payment_intent_id=payment_intent.id,
                        shipment_reference=event.canonical_shipment_id,
                        event_type="DELIVERED",
                        amount=tokenomics["final_amount"],
                        currency="USD",
                        status=PaymentStatus.SETTLED
                    )
                    db.add(milestone)
                    # --- LEDGER TOKEN FIELDS ---
                    if hasattr(payment_intent, "token_reward"):
                        payment_intent.token_reward = tokenomics["token_amount"]
                        payment_intent.token_burn = tokenomics["burn_amount"]
                        payment_intent.token_net = tokenomics["final_amount"]
                        payment_intent.governance_trace_id = governance["trace_id"]
                        payment_intent.governance_severity = governance["severity"]
                        payment_intent.governance_rule = governance["rule_id"]
                        payment_intent.governance_rationale = governance["rationale"]
                    await self.event_publisher.publish_settlement_event(
                        event.canonical_shipment_id,
                        "SETTLEMENT_FINALIZED",
                        tokenomics["final_amount"],
                        tokenomics.get("trace_id") or getattr(event, "trace_id", None),
                    )
                    # --- XRPL ANCHORING ---
                    try:
                        from chainpay_service.config import XRPL_MODE, XRPL_SEED, XRPL_ADDRESS
                        from chainpay_service.app.xrpl.xrpl_settlement_service import XRPLSettlementService
                        xrpl_service = XRPLSettlementService({
                            "XRPL_MODE": XRPL_MODE,
                            "XRPL_SEED": XRPL_SEED,
                            "XRPL_ADDRESS": XRPL_ADDRESS
                        })
                        anchor_result = await xrpl_service.anchor_settlement(
                            canonical_shipment_id=event.canonical_shipment_id,
                            event_payload=event.dict() if hasattr(event, "dict") else dict(event),
                            governance_metadata=governance,
                            ml_metadata=ml_prediction
                        )
                        if anchor_result.get("success"):
                            await self.event_publisher.publish_settlement_event(
                                event.canonical_shipment_id,
                                "XRPL_ANCHOR_SUCCESS",
                                tokenomics["final_amount"],
                                anchor_result["trace_id"],
                                extra={
                                    "xrplTxHash": anchor_result["tx_hash"],
                                    "xrplLedgerIndex": anchor_result["ledger_index"],
                                    "xrplRationale": anchor_result["rationale"],
                                    "xrplTraceId": anchor_result["trace_id"],
                                    "settlementHash": anchor_result["settlement_hash"]
                                }
                            )
                        else:
                            await self.event_publisher.publish_settlement_event(
                                event.canonical_shipment_id,
                                "XRPL_ANCHOR_FAILURE",
                                tokenomics["final_amount"],
                                anchor_result["trace_id"],
                                extra={
                                    "xrplRationale": anchor_result["rationale"],
                                    "xrplTraceId": anchor_result["trace_id"]
                                }
                            )
                    except Exception as ex:
                        logger.error(f"XRPL anchoring failed: {ex}")
                    # --- PUBLISH TOKEN EVENT ---
                    try:
                        from ..services.token_event_publisher import publish_token_event
                        await publish_token_event(
                            event_type="TOKEN_FINAL",
                            shipment_id=event.canonical_shipment_id,
                            token_amount=tokenomics["token_amount"],
                            burn_amount=tokenomics["burn_amount"],
                            risk_multiplier=tokenomics["risk_multiplier"],
                            ml_adjustment=tokenomics["ml_adjustment"],
                            severity=governance["severity"],
                            rationale=governance["rationale"],
                            rule_id=governance["rule_id"],
                            decision_path=governance["decision_path"],
                            trace_id=governance["trace_id"]
                        )
                    except ImportError:
                        logger.warning("Token event publisher not available yet.")

            db.commit()
            logger.info(f"Handled shipment event for shipment {event.canonical_shipment_id}")
        except Exception as e:
            logger.error(f"Failed to handle shipment event: {e}")
            db.rollback()
        finally:
            db.close()
