"""ML-related Pydantic schemas for ChainIQ (AT-02 draft).

This module defines the draft schema for the AT-02 Fraud Assessment
Object and related request/response payloads. It is intentionally
minimal and may be extended by Cody as implementation proceeds.
"""

from __future__ import annotations

from datetime import datetime, date
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class DominantFeature(BaseModel):
    name: str = Field(..., description="Feature name")
    contribution: float = Field(..., description="Absolute or normalized importance")
    direction: Literal["increase", "decrease"] = Field(..., description="Whether this feature pushes fraud score up or down")


class CounterfactualExplanation(BaseModel):
    feature: str = Field(..., description="Actionable feature name")
    from_value: Optional[float | str] = Field(None, alias="from", description="Original value (numeric or categorical)")
    to_value: Optional[float | str] = Field(None, alias="to", description="Proposed value after change")
    delta: Optional[float] = Field(None, description="Numeric difference where applicable (to - from)")
    note: Optional[str] = Field(None, description="Human-readable explanation of the counterfactual change")

    class Config:
        allow_population_by_field_name = True


class TrainingDataWindow(BaseModel):
    start: date
    end: date


class ModelMetadata(BaseModel):
    model_version_id: str
    schema_version: str
    generated_at: datetime
    inference_id: str
    training_data_window: Optional[TrainingDataWindow] = None


class FraudAssessment(BaseModel):
    fraud_score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str
    dominant_features: List[DominantFeature]
    counterfactual: Optional[CounterfactualExplanation] = None
    recommended_action: Literal["approve", "review", "hold", "deny"]
    alex_gate: Literal["pass", "fail"]
    model_metadata: ModelMetadata


class AT02EvaluationContext(BaseModel):
    movement_token_id: Optional[str] = None
    accessorial_token_id: Optional[str] = None
    invoice_token_id: Optional[str] = None
    carrier_id: Optional[str] = None
    facility_id: Optional[str] = None


class AT02EvaluateRequest(BaseModel):
    """Request payload for /ml/at02/evaluate.

    The concrete feature payload schema is defined outside this module;
    here we accept an opaque dictionary validated upstream against the
    AT-02 feature schema.
    """

    schema_version: str = Field(..., description="AT-02 feature schema version")
    context: AT02EvaluationContext
    feature_payload: dict


class AT02EvaluateResponse(BaseModel):
    status: Literal["ok", "error"]
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    fraud_assessment: Optional[FraudAssessment] = None


class AT02ExplainRequest(BaseModel):
    inference_id: str
    accessorial_token_id: Optional[str] = None


class AT02ExplainResponse(BaseModel):
    status: Literal["ok", "error"]
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    explanations: Optional[dict] = None


class AT02CounterfactualRequest(BaseModel):
    inference_id: str
    target_fraud_score: float = Field(..., ge=0.0, le=1.0)
    allowed_features: List[str]


class AT02CounterfactualResponse(BaseModel):
    status: Literal["ok", "error"]
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    counterfactual: Optional[CounterfactualExplanation] = None
