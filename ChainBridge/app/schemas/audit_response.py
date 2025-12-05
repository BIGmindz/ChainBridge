from pydantic import BaseModel
from typing import List, Optional

class MilestoneModel(BaseModel):
    id: Optional[int]
    event_type: Optional[str]
    amount: Optional[float]
    currency: Optional[str]
    status: Optional[str]

class SummaryModel(BaseModel):
    total_approved_amount: Optional[float]
    total_settled_amount: Optional[float]
    total_milestones: Optional[int]

class PaymentIntentModel(BaseModel):
    id: Optional[int]
    freight_token_id: Optional[int]
    amount: Optional[float]
    currency: Optional[str]
    risk_tier: Optional[str]
    status: Optional[str]

class AuditShipmentResponse(BaseModel):
    shipment_id: Optional[int]
    milestones: List[MilestoneModel] = []
    summary: Optional[SummaryModel]

class AuditPaymentIntentResponse(BaseModel):
    payment_intent: Optional[PaymentIntentModel]
    milestones: List[MilestoneModel] = []
    summary: Optional[SummaryModel]
