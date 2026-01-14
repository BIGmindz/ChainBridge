# ChainBridge Vaporizer - IT Handover Manual

**Document Version:** 1.0.0  
**PAC Reference:** PAC-VAPORIZER-DEPLOY-27  
**Classification:** PARTNER CONFIDENTIAL  
**Intended Audience:** Bank IT Department / CTO  

---

## Executive Summary

The **ChainBridge Vaporizer** is a client-side tool that transforms your customer data into cryptographic hashes compatible with ChainBridge's Zero-Knowledge compliance verification system.

**Key Benefits:**
- ✅ **Zero PII Transmission** - Raw data never leaves your servers
- ✅ **Zero Dependencies** - Standard Python library only (3.7+)
- ✅ **Cryptographically Anchored** - Bound to ChainBridge Genesis Block
- ✅ **Memory Safe** - Raw data purged immediately after hashing
- ✅ **CRO Sign-Off Ready** - Full audit trail with zero regulatory exposure

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Installation](#2-installation)
3. [Quick Start](#3-quick-start)
4. [Input Format](#4-input-format)
5. [Output Format (.cbh)](#5-output-format-cbh)
6. [Security Architecture](#6-security-architecture)
7. [Usage Examples](#7-usage-examples)
8. [Verification Procedures](#8-verification-procedures)
9. [Troubleshooting](#9-troubleshooting)
10. [Support Contact](#10-support-contact)

---

## 1. System Requirements

| Requirement | Specification |
|-------------|---------------|
| **Python** | 3.7 or higher |
| **Memory** | 256MB minimum |
| **Disk** | 10MB for script, plus output file |
| **OS** | Windows, macOS, Linux |
| **Dependencies** | None (Standard Library Only) |
| **Network** | NOT REQUIRED for hashing |

### Verifying Python Version

```bash
python --version
# or
python3 --version
```

Expected output: `Python 3.7.x` or higher

---

## 2. Installation

### Step 1: Receive the Vaporizer Package

You will receive a signed package containing:
- `vaporizer.py` - The main script
- `CHECKSUM.sha256` - Integrity verification file
- This manual (PDF/MD)

### Step 2: Verify Script Integrity

Before running, verify the script has not been tampered with:

```bash
# On Linux/macOS:
sha256sum vaporizer.py

# On Windows (PowerShell):
Get-FileHash vaporizer.py -Algorithm SHA256
```

Compare the output with the hash provided in `CHECKSUM.sha256`.

### Step 3: Place in Secure Location

```bash
# Create secure directory
mkdir -p /opt/chainbridge/vaporizer
chmod 700 /opt/chainbridge/vaporizer

# Copy script
cp vaporizer.py /opt/chainbridge/vaporizer/
```

---

## 3. Quick Start

### Run Self-Test

```bash
python vaporizer.py --test
```

Expected output:
```
[TEST] Running Vaporizer Self-Test...
[TEST 1] Basic name hashing...           ✓ PASS
[TEST 2] Normalization consistency...    ✓ PASS
[TEST 3] Hash uniqueness...              ✓ PASS
[TEST 4] Salt binding...                 ✓ PASS
[TEST 5] CBH file integrity...           ✓ PASS
[RESULT] All tests PASSED ✓
```

### Process a CSV File

```bash
python vaporizer.py customers.csv output.cbh
```

### Verify Output File

```bash
python vaporizer.py --verify output.cbh
```

---

## 4. Input Format

The Vaporizer accepts CSV files with the following columns:

### Required Columns

| Column | Description | Example |
|--------|-------------|---------|
| `id` | Unique record identifier | `CUST-001` |
| `first_name` | Customer first name | `John` |
| `last_name` | Customer last name | `Doe` |

### Optional Columns

| Column | Description | Example |
|--------|-------------|---------|
| `dob` | Date of birth | `1985-03-15` |
| `tax_id` | Tax identification number | `123-45-6789` |
| `national_id` | National ID number | `AB1234567` |

### Sample Input File

```csv
id,first_name,last_name,dob,tax_id
CUST-001,John,Doe,1985-03-15,123-45-6789
CUST-002,Jane,Smith,1990-07-22,987-65-4321
CUST-003,Robert,Johnson,1978-11-30,456-78-9012
```

### Data Normalization

The script automatically normalizes input data:
- Converts to lowercase
- Trims whitespace
- Normalizes Unicode characters
- Removes non-printable characters

**Example:** `"  JOHN  "`, `"john"`, and `"John"` all produce the **same hash**.

---

## 5. Output Format (.cbh)

The Vaporizer produces a `.cbh` (ChainBridge Hash) file in JSON format.

### File Structure

```json
{
  "cbh_header": {
    "version": "1.0.0",
    "format_type": "CHAINBRIDGE_HASH",
    "genesis_anchor": "GENESIS-SOVEREIGN-2026-01-14",
    "salt_fingerprint": "31335eaf...646677a6",
    "created_at": "2026-01-14T22:30:00.000000+00:00",
    "total_records": 3,
    "integrity_hash": "abc123..."
  },
  "records": [
    {
      "record_id": "CUST-001",
      "full_name_hash": "7f83b162...",
      "dob_hash": "a9b8c7d6...",
      "tax_id_hash": "1a2b3c4d...",
      "vaporized_at": "2026-01-14T22:30:00.000000+00:00"
    }
  ]
}
```

### Header Fields

| Field | Description |
|-------|-------------|
| `version` | CBH format version |
| `genesis_anchor` | ChainBridge Genesis Block reference |
| `salt_fingerprint` | Partial hash of Sovereign Salt (for verification) |
| `integrity_hash` | SHA-256 of entire file contents |

---

## 6. Security Architecture

### Cryptographic Binding

```
┌─────────────────────────────────────────────────────────────┐
│                    VAPORIZER SECURITY                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Your Data → [Normalization] → [HMAC-SHA256 + Salt] → Hash │
│                                                             │
│   ┌─────────────┐    ┌──────────────┐    ┌────────────┐    │
│   │  Raw PII    │ → │  Normalized   │ → │  64-char   │    │
│   │  "John Doe" │    │  "john|doe"  │    │  Hash      │    │
│   └─────────────┘    └──────────────┘    └────────────┘    │
│          ↓                                                  │
│   [PURGED FROM MEMORY]                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### What IS Transmitted

- ✅ 64-character hexadecimal hashes
- ✅ Record identifiers (non-PII)
- ✅ Timestamps
- ✅ Integrity hash

### What IS NOT Transmitted

- ❌ Names
- ❌ Dates of birth
- ❌ Tax IDs
- ❌ National IDs
- ❌ Any raw PII

### One-Way Transformation

The HMAC-SHA256 algorithm is **mathematically irreversible**:
- Possession of the hash cannot reveal the original data
- Possession of the salt cannot reveal the original data
- Only the original data + salt can recreate the same hash

---

## 7. Usage Examples

### Example 1: Basic CSV Processing

```bash
python vaporizer.py /data/customers.csv /output/customers.cbh
```

### Example 2: Custom Column Mapping

If your CSV has different column names:

```python
from vaporizer import VaporizerEngine, CBHFile

engine = VaporizerEngine()
records = engine.vaporize_csv(
    csv_path="input.csv",
    first_name_col="fname",      # Your column name
    last_name_col="lname",       # Your column name
    record_id_col="customer_id"  # Your column name
)

cbh = CBHFile.from_vaporized_records(records)
cbh.save("output.cbh")
```

### Example 3: Programmatic Single Record

```python
from vaporizer import VaporizerEngine

engine = VaporizerEngine()
record = engine.vaporize_record(
    record_id="CUST-001",
    first_name="John",
    last_name="Doe",
    dob="1985-03-15",
    tax_id="123-45-6789"
)

print(f"Name Hash: {record.full_name_hash}")
print(f"DOB Hash: {record.dob_hash}")
```

---

## 8. Verification Procedures

### Verify Output File Integrity

```bash
python vaporizer.py --verify output.cbh
```

Expected output:
```
[VERIFY] Checking output.cbh...
------------------------------------------------------------
  Version: 1.0.0
  Genesis Anchor: GENESIS-SOVEREIGN-2026-01-14
  Salt Fingerprint: 31335eaf...646677a6
  Total Records: 1000
  Integrity Hash: abc123...
------------------------------------------------------------
[VERIFY] Integrity VERIFIED ✓
```

### Verify Salt Binding

The salt fingerprint should match: `31335eaf...646677a6`

If it does not match, contact ChainBridge support immediately.

### Run Full Validation

```bash
python vaporizer.py --validate 1000
```

This processes 1,000 dummy records to verify system integrity.

---

## 9. Troubleshooting

### Error: "Python not found"

**Solution:** Ensure Python 3.7+ is installed and in your PATH.

```bash
# Linux/macOS
which python3

# Windows
where python
```

### Error: "UnicodeDecodeError"

**Solution:** Ensure your CSV is UTF-8 encoded.

```bash
# Convert to UTF-8 on Linux/macOS
iconv -f ISO-8859-1 -t UTF-8 input.csv > input_utf8.csv
```

### Error: "Permission denied"

**Solution:** Check file permissions.

```bash
chmod +x vaporizer.py
chmod 644 input.csv
```

### Error: "Column not found"

**Solution:** Verify your CSV column names match the expected names or use custom column mapping.

---

## 10. Support Contact

**Technical Support:**
- Email: compliance@chainbridge.io
- Subject Line: [VAPORIZER-SUPPORT] Your Issue

**Emergency Security:**
- Email: security@chainbridge.io
- Phone: +1-XXX-XXX-XXXX (24/7)

**Documentation Updates:**
- https://docs.chainbridge.io/vaporizer

---

## Appendix A: Compliance Attestation

By using this script, you attest that:

1. The script will be executed only on authorized systems
2. Output files (.cbh) will be transmitted via secure channels
3. Input data remains under your organization's control
4. You have verified the script's integrity hash before execution

**ChainBridge Zero-PII Compliance Statement:**

> "The Vaporizer script transforms personally identifiable information (PII) into 
> cryptographic hashes using HMAC-SHA256 with a Sovereign Salt anchored to the 
> ChainBridge Genesis Block. Raw data exists only in memory during processing 
> and is explicitly purged after transformation. No PII is stored, transmitted, 
> or retained by this script."

---

**Document Hash:** `[To be computed on final version]`  
**Approved By:** ARCHITECT-JEFFREY  
**Executor:** BENSON-GID-00  
**PAC Reference:** PAC-VAPORIZER-DEPLOY-27  
