"""
Event schema validation for ChainBridge ML ingestion.
Aligns with /common/events/ schemas.
"""

import json
from jsonschema import validate, ValidationError
from .config import EVENT_SCHEMA

def validate_event_schema(event_json):
    try:
        event = json.loads(event_json)
        validate(instance=event, schema=EVENT_SCHEMA)
        return event
    except (ValidationError, json.JSONDecodeError):
        return None
