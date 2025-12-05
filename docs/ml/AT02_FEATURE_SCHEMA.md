# AT-02 Feature Schema v1

## 1. BLUF

AT-02 uses a glass-box, token-aware feature schema to detect falsified or inflated accessorials (detention, layover, reclassification, TONU, liftgate, etc.) by combining IoT telemetry, route timelines, carrier history, and document metadata. All features are engineered to be auditable, explainable, and compatible with monotonic GBMs/GAMs and SHAP-based attribution.

Each feature below is defined with:
- **Name**
- **Type** (numeric, categorical, boolean, timestamp, enum)
- **Unit / Domain**
- **Source** (IoT, TMS, WMS, ERP, docs, token graph)
- **Rationale** (why it matters for fraud)
- **Monotonic Expectation** (↑ should increase or decrease fraud risk, or non-monotonic)

---

## 2. Entity & Event Model

AT-02 operates over a single **accessorial claim event**, linked to:
- **Shipment / Movement**: MT-01 (Movement Token)
- **Accessorial Token**: AT-02 instance
- **Invoice Line**: IT-01 linkage
- **Carrier Profile**: CCT-01 aggregates
- **Timeline & IoT Stream**: GPS, telematics, temperature, door sensors, etc.

All features should be mappable to one or more of:
- `movement_token_id`
- `accessorial_token_id`
- `invoice_token_id`
- `carrier_id`
- `facility_id`
- `device_id`

These IDs themselves are not predictive features; they index into histories from which aggregate, explainable signals are derived.

---

## 3. Core Feature Groups

### 3.1. Accessorial Claim Descriptor Features

1. **`accessorial_type`**
   - Type: categorical (enum)
   - Domain: {DETENTION, LAYOVER, TONU, LIFTGATE, RECLASSIFICATION, REDLIVERY, STORAGE, HAZMAT, FUEL_SURCHARGE, OTHER}
   - Source: AT-02 token payload, TMS
   - Rationale: Different accessorials have different baseline risk profiles and expected patterns.
   - Monotonic: Non-monotonic (handled via one-hot / target encoding in glass-box model).

2. **`claimed_amount_usd`**
   - Type: numeric (float)
   - Unit: USD
   - Source: IT-01 invoice line
   - Rationale: Large claimed amounts increase financial risk; extreme outliers may be fraudulent.
   - Monotonic: Generally ↑ amount → ↑ fraud risk (monotonic increasing, with care for high but legitimate cases).

3. **`contractual_reference_rate_usd`**
   - Type: numeric (float)
   - Unit: USD
   - Source: Contract / rate table
   - Rationale: Comparison point to detect overbilling.
   - Monotonic: Higher contract rate → neutral/non-monotonic; difference to claimed is more important.

4. **`claimed_vs_contract_ratio`**
   - Type: numeric (float)
   - Unit: ratio
   - Source: derived: `claimed_amount_usd / contractual_reference_rate_usd`
   - Rationale: Direct signal of overbilling (ratio >> 1) or underbilling.
   - Monotonic: ↑ ratio → ↑ fraud risk (monotonic increasing, capped/winsorized).

5. **`accessorial_reason_code`**
   - Type: categorical (enum/string bucket)
   - Domain: normalized set (e.g., `SHIPPER_NOT_READY`, `FACILITY_DELAY`, `CARRIER_ISSUE`, `WEATHER`, `SECURITY`, etc.)
   - Source: TMS, carrier EDI/portal
   - Rationale: Certain reason codes are historically abused; mismatches with IoT data are red flags.
   - Monotonic: Non-monotonic.

6. **`accessorial_claim_timestamp_utc`**
   - Type: timestamp
   - Unit: UTC
   - Source: TMS / AT-02 token mint time
   - Rationale: Used to align with movement timeline and IoT data.
   - Monotonic: Not directly; transformed into derived time-based features.

7. **`accessorial_claim_entry_lag_minutes`**
   - Type: numeric (float)
   - Unit: minutes
   - Source: difference between event time and entry time
   - Rationale: Very late backfilled claims (days after event) can indicate manipulation.
   - Monotonic: ↑ lag → ↑ fraud risk (monotonic increasing, with thresholding).

---

### 3.2. IoT-Derived Dwell & Movement Features

Assume we have a time series of GPS + device events around the window of claimed accessorial.

8. **`dwell_duration_observed_minutes`**
   - Type: numeric (float)
   - Unit: minutes
   - Source: IoT/GPS (vehicle stationary within geofence)
   - Rationale: Ground truth dwell time vs claimed detention/layover window.
   - Monotonic: For detention, ↑ observed dwell beyond free-time → ↑ legitimate accessorial likelihood; for fraud, discordance with claimed window is key (handled via delta features below).

9. **`claimed_dwell_duration_minutes`**
   - Type: numeric (float)
   - Unit: minutes
   - Source: accessorial claim
   - Rationale: Basis for comparison.
   - Monotonic: Non-monotonic alone; use deltas.

10. **`dwell_duration_delta_minutes`**
    - Type: numeric (float)
    - Unit: minutes
    - Source: `claimed_dwell_duration_minutes - dwell_duration_observed_minutes`
    - Rationale: Positive deltas (claim > observed) indicate overstatement.
    - Monotonic: ↑ delta → ↑ fraud risk (monotonic increasing, clipped).

11. **`num_geofence_entries_exits`**
    - Type: integer
    - Unit: count
    - Source: GPS/geofence events
    - Rationale: Multiple entries/exits vs a single long dwell can indicate timeline manipulation or poor data quality.
    - Monotonic: Non-monotonic (used with context).

12. **`max_speed_within_facility_mph`**
    - Type: numeric (float)
    - Unit: mph
    - Source: IoT speed
    - Rationale: High speeds inside a supposed dwell window suggest GPS/timestamp issues.
    - Monotonic: ↑ max speed within dwell → ↑ fraud risk (monotonic increasing, with facility-specific caps).

13. **`movement_gap_before_claim_minutes`**
    - Type: numeric (float)
    - Unit: minutes
    - Source: time from last movement to claim start
    - Rationale: Very short gap may indicate misaligned timestamps; very long gaps may suggest stale data.
    - Monotonic: Non-monotonic; binned or via GAM.

14. **`movement_gap_after_claim_minutes`**
    - Type: numeric (float)
    - Unit: minutes
    - Source: time from claim end to next movement
    - Rationale: Should align with realistic load/unload behavior.
    - Monotonic: Non-monotonic.

15. **`gps_signal_quality_score`**
    - Type: numeric (0–1)
    - Source: sensor metadata (HDOP, satellite count, etc.)
    - Rationale: Low signal quality weakens IoT evidence; ALEX may require proofPack supplementation.
    - Monotonic: ↓ quality → ↑ uncertainty & governance friction (used for confidence modeling, not pure fraud score).

16. **`iot_message_dropout_rate`**
    - Type: numeric (0–1)
    - Unit: fraction of expected messages missing in window
    - Source: IoT stream
    - Rationale: High dropout may be benign (coverage) or adversarial (device powering off).
    - Monotonic: ↑ dropout → ↑ uncertainty and possible fraud risk.

---

### 3.3. Timeline Deviation Features

17. **`scheduled_appointment_start_utc`** / **`scheduled_appointment_end_utc`**
    - Type: timestamps
    - Source: TMS / facility
    - Rationale: Compare actual vs scheduled windows.

18. **`arrival_vs_appointment_minutes`**
    - Type: numeric (float)
    - Unit: minutes
    - Source: actual arrival (from IoT) vs appointment start
    - Rationale: Early/late arrivals may or may not justify detention.
    - Monotonic: Non-monotonic; binned and used with reason codes.

19. **`departure_vs_appointment_minutes`**
    - Type: numeric (float)
    - Unit: minutes
    - Source: departure time vs appointment end
    - Rationale: Extended stay beyond appointment window may be legitimate detention or suspicious.
    - Monotonic: ↑ positive deviation → ↑ legitimate detention; misalignment with claim drives fraud score.

20. **`claimed_detention_window_start_utc` / `claimed_detention_window_end_utc`**
    - Type: timestamps
    - Source: accessorial claim
    - Rationale: Define claimed window for delta features.

21. **`detention_window_alignment_score`**
    - Type: numeric (0–1)
    - Source: overlap between claimed window and observed dwell window
    - Rationale: Low overlap indicates falsified or misaligned claims.
    - Monotonic: ↓ alignment → ↑ fraud risk (monotonic decreasing or use (1 - alignment) as feature).

22. **`backfill_indicator`**
    - Type: boolean
    - Source: whether claim was entered > X days after event
    - Rationale: Backfilled claims are higher risk.
    - Monotonic: True → ↑ fraud risk.

---

### 3.4. Carrier Historical Behavior Features

23. **`carrier_accessorial_frequency_30d`**
    - Type: numeric (float)
    - Unit: accessorials per 100 loads (last 30 days)
    - Source: historical AT-02s per carrier
    - Rationale: High frequency accessorial issuers may be gaming contracts.
    - Monotonic: ↑ frequency → ↑ baseline fraud risk.

24. **`carrier_accessorial_frequency_by_type_30d`**
    - Type: numeric per type
    - Unit: per 100 loads
    - Rationale: Some carriers overuse specific accessorials (e.g., detention).
    - Monotonic: ↑ type-specific frequency → ↑ risk for that accessorial type.

25. **`carrier_dispute_rate_90d`**
    - Type: numeric (0–1)
    - Unit: fraction of accessorials disputed
    - Source: ChainIQ / billing history
    - Rationale: High dispute rates flag systemic issues.
    - Monotonic: ↑ dispute rate → ↑ fraud risk.

26. **`carrier_dispute_loss_rate_90d`**
    - Type: numeric (0–1)
    - Unit: fraction of disputes lost by carrier
    - Rationale: If disputes consistently resolve against carrier, their future claims are suspect.
    - Monotonic: ↑ loss rate → ↑ fraud risk.

27. **`carrier_facility_pair_anomaly_score`**
    - Type: numeric (0–1)
    - Source: unsupervised/anomaly model over (carrier, facility) pairs
    - Rationale: Certain carrier–facility combos may exhibit odd patterns.
    - Monotonic: ↑ anomaly score → ↑ fraud risk.

28. **`carrier_credit_tier`** (from CCT-01)
    - Type: categorical (e.g., A, B, C, D)
    - Source: CCT-01 token
    - Rationale: Lower tiers may correlate with higher accessorial risk.
    - Monotonic: Encoded monotonically (A→lowest, D→highest fraud risk).

---

### 3.5. Shipment & Movement Context Features (MT-01 Alignment)

29. **`lane_type`**
    - Type: categorical
    - Domain: {LTL, TL, PARCEL, INTERMODAL}
    - Source: MT-01
    - Rationale: Accessorial norms differ by mode.
    - Monotonic: Non-monotonic.

30. **`distance_miles`**
    - Type: numeric
    - Unit: miles
    - Source: route geometry
    - Rationale: Very short-haul loads with large detention claims are suspect.
    - Monotonic: Non-monotonic; combined with claim size.

31. **`origin_facility_type` / `destination_facility_type`**
    - Type: categorical (e.g., DC, store, crossdock, port, rail yard)
    - Source: facility master
    - Rationale: Different facility types have different dwell norms.
    - Monotonic: Non-monotonic.

32. **`historical_avg_dwell_for_facility_minutes`**
    - Type: numeric (float)
    - Unit: minutes
    - Source: aggregated IoT history
    - Rationale: Compares this event to facility-level baseline.
    - Monotonic: ↑ (claimed - baseline) → ↑ fraud risk, if unsupported by IoT.

33. **`num_prior_shipments_this_lane_90d`**
    - Type: integer
    - Unit: count
    - Source: MT-01 history
    - Rationale: Data density for this lane; low density → higher uncertainty.
    - Monotonic: Non-monotonic; used for confidence, not fraud.

34. **`mt01_etd_vs_actual_departure_delta_minutes`**
    - Type: numeric (float)
    - Unit: minutes
    - Source: planned vs actual
    - Rationale: Late departures might justify detention; misalignment with claims is a flag.
    - Monotonic: Non-monotonic.

35. **`mt01_eta_vs_actual_arrival_delta_minutes`**
    - Type: numeric (float)
    - Unit: minutes
    - Source: planned vs actual
    - Rationale: Very late arrivals may shift responsibility from facility to carrier.
    - Monotonic: Non-monotonic, used in causal reasoning about liability.

---

### 3.6. Document & Metadata Features (IT-01, BOL, POD)

36. **`bol_present`**
    - Type: boolean
    - Source: document system
    - Rationale: Missing BOL when claiming accessorial is suspicious.
    - Monotonic: False → ↑ fraud risk.

37. **`pod_present`**
    - Type: boolean
    - Source: document system
    - Rationale: Missing POD weakens validation.
    - Monotonic: False → ↑ fraud risk.

38. **`doc_ocr_confidence_score`**
    - Type: numeric (0–1)
    - Source: OCR pipeline
    - Rationale: Low confidence may indicate tampering or low-quality scans.
    - Monotonic: ↓ confidence → ↑ uncertainty & potential fraud.

39. **`doc_edit_history_length`**
    - Type: integer
    - Unit: number of edits/versions
    - Source: document management system
    - Rationale: Many edits close to billing time can be suspicious.
    - Monotonic: ↑ edits → ↑ fraud risk.

40. **`signature_match_score`**
    - Type: numeric (0–1)
    - Source: signature verification model
    - Rationale: Low match to known signatories suggests forgery.
    - Monotonic: ↓ score → ↑ fraud risk.

41. **`handwritten_adjustment_indicator`**
    - Type: boolean
    - Source: OCR/vision
    - Rationale: Handwritten, last-minute modifications are higher risk.
    - Monotonic: True → ↑ fraud risk.

42. **`free_text_dispute_language_score`**
    - Type: numeric (0–1)
    - Source: NLP over free text, tuned to **non-sensitive, non-PII** phrases
    - Rationale: Detects language patterns associated with disputes and justifications.
    - Monotonic: ↑ score → ↑ fraud risk (for accessorial justification text).

---

### 3.7. Anomaly & Exploit Pattern Features

43. **`carrier_accessorial_spike_zscore_7d`**
    - Type: numeric (float)
    - Unit: z-score
    - Source: time-series over accessorial counts
    - Rationale: Short-term spikes can indicate exploit campaigns.
    - Monotonic: ↑ z-score → ↑ fraud risk.

44. **`facility_accessorial_spike_zscore_7d`**
    - Type: numeric (float)
    - Unit: z-score
    - Rationale: Facility-specific issues or collusion.
    - Monotonic: ↑ z-score → ↑ fraud risk.

45. **`similar_claims_in_batch_count`**
    - Type: integer
    - Unit: count of nearly identical claims in billing batch
    - Rationale: Batch padding pattern.
    - Monotonic: ↑ count → ↑ fraud risk.

46. **`batch_claim_amount_concentration_ratio`**
    - Type: numeric (0–1)
    - Unit: share of total accessorial amount in a few claims
    - Rationale: High concentration indicates targeted inflation.
    - Monotonic: ↑ concentration → ↑ fraud risk.

47. **`historical_false_positive_flag_rate`**
    - Type: numeric (0–1)
    - Source: governance feedback loop
    - Rationale: Used to tune thresholds and calibrate risk for a given feature cluster.
    - Monotonic: Non-monotonic; used for calibration.

---

### 3.8. Security & Tamper Features

48. **`device_reboot_count_in_window`**
    - Type: integer
    - Unit: count
    - Source: IoT logs
    - Rationale: Multiple reboots during dwell/detention windows can indicate tampering.
    - Monotonic: ↑ reboots → ↑ fraud risk.

49. **`device_location_jumps_over_threshold_count`**
    - Type: integer
    - Unit: count
    - Source: GPS
    - Rationale: Teleport-like jumps indicate spoofing.
    - Monotonic: ↑ jumps → ↑ fraud risk.

50. **`time_sync_discrepancy_seconds`**
    - Type: numeric (float)
    - Unit: seconds
    - Source: difference between device clock and authoritative time
    - Rationale: Manually adjusted clocks are a classic tampering pattern.
    - Monotonic: ↑ discrepancy → ↑ fraud risk.

51. **`multi_device_inconsistency_score`**
    - Type: numeric (0–1)
    - Source: comparison of multiple IoT devices on same asset
    - Rationale: Conflicting readings suggest spoofing or cloning.
    - Monotonic: ↑ inconsistency → ↑ fraud risk.

---

### 3.9. Governance & Confidence Features

52. **`data_completeness_score`**
    - Type: numeric (0–1)
    - Source: feature-level missingness
    - Rationale: Low completeness = higher uncertainty; ALEX may require proofPack reinforcement.
    - Monotonic: ↓ completeness → ↓ confidence (uncertainty up, not directly fraud up).

53. **`num_critical_features_missing`**
    - Type: integer
    - Source: subset of mandatory features (e.g., dwell, contract rate)
    - Rationale: Missing critical fields lead to HOLD/REVIEW even if fraud score moderate.
    - Monotonic: ↑ missing → ↓ confidence and ↑ governance friction.

54. **`model_version_id`**
    - Type: categorical/string
    - Rationale: Governance & lineage; not used for prediction.

---

## 4. Feature Engineering Patterns

- **Raw → Normalized:**
  - Standardize units (minutes, miles, USD) and normalize ratios.
- **Normalized → Domain Features:**
  - Deltas (claimed vs observed), alignment scores, z-scores.
- **Domain → Predictive Features:**
  - Monotonic transformations (e.g., `max(0, claimed_vs_contract_ratio - 1)`), bins, and interaction terms that remain explainable.
- **Predictive → Explainability Features:**
  - Group features into human-readable buckets for dashboards: IoT vs Contract vs History vs Documents vs Security vs Governance.

All features must be:
- Deterministically computable from logged data
- Versioned (schema version + model version)
- Auditable (traceable to source systems)

---

## 5. Token Alignment

- **AT-02 (Accessorial Token):**
  - Anchors the specific accessorial event.
- **MT-01 (Movement Token):**
  - Supplies route, dwell, and IoT context.
- **IT-01 (Invoice Token):**
  - Provides financial amounts and billing batch context.
- **CCT-01 (Carrier Credit Token):**
  - Provides carrier tiering and behavioral risk aggregates.

Each feature must be mappable to at least one token and loggable for later forensics, ALEX reviews, and SxT ProofPack verification.
