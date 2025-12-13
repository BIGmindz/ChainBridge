"""
ChainIQ Shadow Mode Migration

Creates risk_shadow_events table for tracking parallel ML model executions.
Run this migration before enabling shadow mode.
"""

-- Migration: 001_shadow_mode_tables
-- Date: 2025-12-11
-- Service: chainiq-service

-- Create risk_shadow_events table
CREATE TABLE IF NOT EXISTS risk_shadow_events (
    id SERIAL PRIMARY KEY,
    shipment_id VARCHAR(255) NOT NULL,
    dummy_score FLOAT NOT NULL,
    real_score FLOAT NOT NULL,
    delta FLOAT NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    corridor VARCHAR(10),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_shadow_events_shipment
    ON risk_shadow_events(shipment_id);

CREATE INDEX IF NOT EXISTS idx_shadow_events_created
    ON risk_shadow_events(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_shadow_events_corridor
    ON risk_shadow_events(corridor);

CREATE INDEX IF NOT EXISTS idx_shadow_events_delta
    ON risk_shadow_events(delta DESC);

-- Add comments
COMMENT ON TABLE risk_shadow_events IS
    'Tracks parallel executions of dummy vs real risk models for validation';

COMMENT ON COLUMN risk_shadow_events.shipment_id IS
    'Shipment identifier for correlation';

COMMENT ON COLUMN risk_shadow_events.dummy_score IS
    'Score from DummyRiskModel (production baseline)';

COMMENT ON COLUMN risk_shadow_events.real_score IS
    'Score from RealRiskModel_v0.2 (candidate for promotion)';

COMMENT ON COLUMN risk_shadow_events.delta IS
    'Absolute difference between scores |dummy - real|';

COMMENT ON COLUMN risk_shadow_events.model_version IS
    'Version identifier of real model (e.g., v0.2.0)';

COMMENT ON COLUMN risk_shadow_events.corridor IS
    'Trade corridor for segmented analysis (e.g., US-MX)';
