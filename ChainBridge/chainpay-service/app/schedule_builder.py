"""
Schedule builder for milestone-based payment settlement.

This module provides helper functions to build default payment schedules
based on freight token risk scores.

Risk-based milestone allocation:
- LOW-risk (0.0-0.33):       20% at PICKUP_CONFIRMED, 70% at POD_CONFIRMED, 10% at CLAIM_WINDOW_CLOSED
- MEDIUM-risk (0.33-0.67):   10% at PICKUP_CONFIRMED, 70% at POD_CONFIRMED, 20% at CLAIM_WINDOW_CLOSED
- HIGH-risk (0.67-1.0):       0% at PICKUP_CONFIRMED, 80% at POD_CONFIRMED, 20% at CLAIM_WINDOW_CLOSED

The order field controls the sequence in which milestones occur.
"""

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class RiskTierSchedule(str, Enum):
    """Risk tier enum for schedule determination."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def risk_score_to_tier(risk_score: float | None) -> RiskTierSchedule:
    """
    Map a risk score (0.0-1.0) to a RiskTierSchedule.
    
    Args:
        risk_score: Risk score from 0.0 to 1.0 (or None for default to MEDIUM)
        
    Returns:
        RiskTierSchedule enum value
    """
    if risk_score is None:
        return RiskTierSchedule.MEDIUM
    
    if risk_score < 0.33:
        return RiskTierSchedule.LOW
    elif risk_score < 0.67:
        return RiskTierSchedule.MEDIUM
    else:
        return RiskTierSchedule.HIGH


def build_default_schedule(risk_tier: RiskTierSchedule) -> list[dict]:
    """
    Build default milestone schedule based on risk tier.
    
    Returns a list of dicts with keys: event_type, percentage, order
    
    Args:
        risk_tier: RiskTierSchedule (LOW, MEDIUM, or HIGH)
        
    Returns:
        List of schedule items for insertion into PaymentScheduleItem table
    """
    schedules = {
        RiskTierSchedule.LOW: [
            {
                "event_type": "PICKUP_CONFIRMED",
                "percentage": 0.20,
                "order": 1,
            },
            {
                "event_type": "POD_CONFIRMED",
                "percentage": 0.70,
                "order": 2,
            },
            {
                "event_type": "CLAIM_WINDOW_CLOSED",
                "percentage": 0.10,
                "order": 3,
            },
        ],
        RiskTierSchedule.MEDIUM: [
            {
                "event_type": "PICKUP_CONFIRMED",
                "percentage": 0.10,
                "order": 1,
            },
            {
                "event_type": "POD_CONFIRMED",
                "percentage": 0.70,
                "order": 2,
            },
            {
                "event_type": "CLAIM_WINDOW_CLOSED",
                "percentage": 0.20,
                "order": 3,
            },
        ],
        RiskTierSchedule.HIGH: [
            {
                "event_type": "PICKUP_CONFIRMED",
                "percentage": 0.0,
                "order": 1,
            },
            {
                "event_type": "POD_CONFIRMED",
                "percentage": 0.80,
                "order": 2,
            },
            {
                "event_type": "CLAIM_WINDOW_CLOSED",
                "percentage": 0.20,
                "order": 3,
            },
        ],
    }
    
    schedule = schedules.get(risk_tier, schedules[RiskTierSchedule.MEDIUM])
    
    logger.info(f"Built default schedule for risk_tier={risk_tier}: {len(schedule)} milestones")
    
    return schedule


def validate_schedule_percentages(schedule: list[dict]) -> bool:
    """
    Validate that schedule percentages sum to 1.0 (within floating-point tolerance).
    
    Args:
        schedule: List of schedule items with 'percentage' key
        
    Returns:
        True if valid, raises ValueError otherwise
    """
    total = sum(item.get("percentage", 0.0) for item in schedule)
    tolerance = 0.01  # Allow 1% tolerance for floating-point rounding
    
    if abs(total - 1.0) > tolerance:
        raise ValueError(
            f"Schedule percentages sum to {total:.2f}, expected 1.0 (tolerance: {tolerance})"
        )
    
    return True


def calculate_milestone_amount(total_amount: float, milestone_percentage: float) -> float:
    """
    Calculate the settlement amount for a specific milestone.
    
    Args:
        total_amount: Total payment intent amount
        milestone_percentage: Percentage for this milestone (0.0-1.0)
        
    Returns:
        Calculated milestone settlement amount
    """
    amount = total_amount * milestone_percentage
    return round(amount, 2)  # Round to 2 decimal places for currency
