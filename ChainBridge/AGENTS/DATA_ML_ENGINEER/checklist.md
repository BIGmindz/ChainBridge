# DATA_ML_ENGINEER – Quick-Start Checklist

1. Review canonical Shipment/Milestone schema and event lifecycle.
2. Build a starter feature notebook using synthetic shipment + IoT data.
3. Implement a baseline risk model:
   - late pickup
   - temperature deviation
   - route deviation
4. Design the `/api/chainiq/score` response schema with Cody.
5. Implement a Pydantic model for risk inference output.
6. Add explainability fields (e.g. "temp_spike=12°F above norm").
7. Define anomaly detection rules for IoT telemetry.
8. Set up model versioning folder and registry structure.
9. Create a test suite for:
   - scoring correctness
   - feature transformations
   - anomaly detection edge cases
10. Coordinate with Sonny to confirm what fields the UI needs for:
    - risk banner
    - warnings panel
    - anomaly alerts
