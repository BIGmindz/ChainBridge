WHAT YOU SHOULD KNOW DEEPLY
- Pandas for feature engineering
- scikit-learn for classical ML
- LightGBM/XGBoost for tabular models
- Time-series feature extraction
- Anomaly detection patterns
- Distributed or streaming data basics
- Data validation (Pydantic, Great Expectations)
- Model monitoring & drift detection

WHAT YOU SHOULD KNOW AT A HIGH LEVEL
- ChainPay settlement lifecycle
- Shipment → ProofPack → Settlement flow
- Corridor structures (origin, destination, carrier, route)
- IoT sensor attributes (temp, humidity, shock, GPS, battery)
- EDI events and what they mean (940/945/856/210)

WHAT YOU SHOULD IGNORE
- UI implementation and layout
- Smart contract specifics
- Advanced blockchain internals
- Deep ML architectures (LSTMs, Transformers) unless needed later

SERVICES YOU INTERACT WITH
- ChainIQ service (your home)
- ChainPay backend (consumes your results)
- ChainBoard frontend (displays your results)
- Seeburger BIS integration layer
- IoT/ChainSense event source

ARCHITECTURAL AWARENESS REQUIRED
- Canonical IDs
- Deterministic scoring outputs
- Full traceability of model input → output
- Stable inference API contracts
- Model version tracking
- Handling missing/late/duplicated events gracefully
