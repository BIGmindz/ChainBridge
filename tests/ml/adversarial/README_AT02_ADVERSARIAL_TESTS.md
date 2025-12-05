# AT-02 Adversarial Experiment Suite — Test Specs (for Sam)

## 1. BLUF

This document specifies the **adversarial test scenarios** for the AT-02 Accessorial Fraud Detection Engine. The goal is to actively attack the model and its data assumptions to ensure robustness against hostile or collusive actors.

Sam and the security team will use these specs to implement automated tests under `tests/ml/adversarial/`.

---

## 2. Threat Model Summary

Adversaries include:
- Carriers inflating or fabricating accessorials.
- Drivers colluding with facilities.
- Malicious insiders altering timestamps or documents.
- Attackers tampering with IoT devices (GPS, telematics).

Attack surfaces:
- GPS location and dwell times.
- Timestamps (arrival, departure, claim entry).
- Accessorial amounts and reason codes.
- IoT device behavior (dropouts, reboots).
- Document metadata (BOL, POD, OCR text).

---

## 3. Scenario Catalog

Each scenario describes **how to perturb data** and **what we expect AT-02 to do**.

### Scenario A: GPS Spoof — Short Dwell, Long Claim

- **Baseline:**
  - Legitimate detention event with observed dwell ≈ claimed dwell.
- **Attack:**
  - Modify GPS data to show only a short dwell (e.g., 30 minutes) while claim asserts 3 hours.
  - Alternatively, shift GPS points to just outside the geofence.
- **Expected Outcome:**
  - `dwell_duration_observed_minutes` << `claimed_dwell_duration_minutes`.
  - `dwell_duration_delta_minutes` large positive.
  - `detention_window_alignment_score` low.
  - Fraud score should **increase significantly**.

### Scenario B: Timestamp Backfill — Late Claim Entry

- **Baseline:**
  - Claim entered within 24 hours of event.
- **Attack:**
  - Modify `accessorial_claim_entry_lag_minutes` to represent several days delay.
  - Backdate or forward-date event timestamps to make audit trails confusing.
- **Expected Outcome:**
  - `backfill_indicator = true`.
  - Model should flag this as higher risk; fraud_score should rise.

### Scenario C: Batch Accessorial Inflation

- **Baseline:**
  - Mixed batch of invoices with a variety of accessorials.
- **Attack:**
  - Create a batch where many claims have:
    - Similar high `claimed_vs_contract_ratio`.
    - Similar `accessorial_type` and reason.
  - Inflate `batch_claim_amount_concentration_ratio`.
- **Expected Outcome:**
  - `similar_claims_in_batch_count` and `batch_claim_amount_concentration_ratio` high.
  - Fraud scores for these claims should increase vs. isolated baseline.

### Scenario D: IoT Dropouts During Detention Window

- **Baseline:**
  - Full IoT coverage around the facility dwell.
- **Attack:**
  - Remove or zero-out IoT messages in the detention window.
  - Simulate device being turned off.
- **Expected Outcome:**
  - `iot_message_dropout_rate` high.
  - `data_completeness_score` reduced.
  - Fraud_score may rise modestly, but **confidence should drop**.
  - Recommended action should avoid auto-deny; prefer `hold`/`review`.

### Scenario E: Device Cloning / Multi-Device Inconsistency

- **Baseline:**
  - Single IoT device per asset with consistent readings.
- **Attack:**
  - Introduce conflicting readings from two devices on the same asset.
  - E.g., one device shows truck parked, another moving.
- **Expected Outcome:**
  - `multi_device_inconsistency_score` high.
  - Fraud_score should increase, especially if supportive of an inflated claim.

### Scenario F: Fraudulent Reclassification

- **Baseline:**
  - Proper accessorial type and amounts aligned with contract.
- **Attack:**
  - Change `accessorial_type` to a more expensive category (e.g., detention → layover) without timeline support.
  - Increase `claimed_amount_usd` accordingly.
- **Expected Outcome:**
  - `claimed_vs_contract_ratio` and related features spike.
  - Fraud_score increases vs. baseline.

### Scenario G: Document Forgery / Signature Mismatch

- **Baseline:**
  - BOL and POD present, high `doc_ocr_confidence_score`, high `signature_match_score`.
- **Attack:**
  - Lower `signature_match_score` to simulate forgery.
  - Increase `doc_edit_history_length` near billing time.
- **Expected Outcome:**
  - Fraud_score should increase.
  - Explanations should highlight document-related features.

### Scenario H: GPS Falsification for Exoneration

- **Baseline:**
  - Legitimate detention; IoT supports claim.
- **Attack:**
  - Modify GPS to show the truck left earlier than it did, indirectly making the facility look more at fault.
- **Expected Outcome:**
  - Misalignment between claim and altered IoT should still be detected.
  - Fraud_score should remain moderate or high if tampering evident.

---

## 4. Test Harness Expectations

- Implement utility functions to:
  - Load a baseline test fixture (JSON with feature payloads).
  - Apply perturbations per scenario.
  - Call the AT-02 scoring function or API.

- For each scenario, assert:
  - Directional changes in `fraud_score` and/or `confidence` vs. baseline.
  - That relevant features appear in `dominant_features`.

---

## 5. Output & Reporting

- Tests should produce:
  - Per-scenario metrics and deltas.
  - Summary table of which attacks significantly affect fraud_score.

- Critical expectation:
  - No simple, single-dimensional attack should consistently drive fraud_score **down** for clearly worse behavior.

---

## 6. Future Extensions

- Add whitebox adversarial perturbation tests directly on feature vectors.
- Add simulated collusion patterns (carrier + facility) over time.
- Link tests into CI so that any model or schema changes must **pass adversarial suite** before deployment.
