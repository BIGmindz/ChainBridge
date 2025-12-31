#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Control Plane — Governance Lint Rules
# PAC-JEFFREY-P07: Lint v2 Law — Runtime & CI Enforcement Implementation
# Supersedes: PAC-JEFFREY-C07R (LAW), PAC-JEFFREY-P06R
# GOLD STANDARD · FAIL_CLOSED
# ═══════════════════════════════════════════════════════════════════════════════
#
# DAN (GID-07) — CI/CD Lane
#
# This script enforces PAC-JEFFREY-P07 governance requirements:
# 1. Lint forbidden timestamps (non-deterministic)
# 2. Lint missing schema references
# 3. Block provisional BER export
# 4. Validate execution_mode and ber_finality fields
# 5. Validate P03 hardening classes (ExecutionBarrier, PackImmutability)
# 6. Validate P03 invariants (INV-CP-013 through INV-CP-016)
# 7. Validate P03 lane authorization
# 8. Validate P04 Settlement Readiness (INV-CP-017 through INV-CP-020)
# 9. Validate P06R Lint v2 invariant engine (S/M/X/T/A/F/C-INV classes)
# 10. Validate P07 runtime activation and agent roster
#
# Usage:
#   ./lint-governance.sh [path]
#
# Exit codes:
#   0 - All checks passed
#   1 - Governance violations detected (FAIL_CLOSED)
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/../.."
SEARCH_PATH="${1:-$PROJECT_ROOT}"
VIOLATIONS=0

echo -e "${CYAN}════════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  ChainBridge Governance Linter — PAC-JEFFREY-P07${NC}"
echo -e "${CYAN}  FAIL_CLOSED Mode · All violations are HARD FAIL${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 1: Forbidden Timestamps in Governance Paths
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}[CHECK 1] Scanning for forbidden non-deterministic timestamps in governance paths...${NC}"

# Governance-critical paths only (control_plane, governance, BER/WRAP/PAC handling)
GOVERNANCE_PATHS=(
    "$PROJECT_ROOT/core/governance"
    "$PROJECT_ROOT/api/controlplane_oc.py"
    "$PROJECT_ROOT/api/governance_oc.py"
)

# Patterns that indicate non-deterministic timestamps
FORBIDDEN_PATTERNS=(
    'datetime\.now\(\s*\)'                     # Python datetime.now() without timezone
    'new Date\(\s*\)'                          # JS new Date() without explicit time
    'Date\.now\(\)'                            # JS Date.now()
    'time\.time\(\)'                           # Python time.time()
    '"timestamp":\s*null'                      # Null timestamps
    '"emitted_at":\s*null'                     # Null emission times
)

CHECK1_VIOLATIONS=0
for gov_path in "${GOVERNANCE_PATHS[@]}"; do
    if [[ -e "$gov_path" ]]; then
        for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
            matches=$(grep -rn --include="*.py" --include="*.ts" --include="*.tsx" \
                -E "$pattern" "$gov_path" 2>/dev/null || true)
            if [[ -n "$matches" ]]; then
                # Filter out test files, comments, timezone-aware calls, simulator and adversarial utilities
                filtered=$(echo "$matches" | grep -v "test_" | grep -v "_tests\.py" | grep -v "#.*$pattern" | grep -v "timezone.utc" | grep -v "simulator" | grep -v "Simulator" | grep -v "adversarial" || true)
                if [[ -n "$filtered" ]]; then
                    echo -e "${RED}  ✗ Found forbidden pattern: $pattern${NC}"
                    echo "$filtered" | head -5
                    ((CHECK1_VIOLATIONS++))
                    ((VIOLATIONS++))
                fi
            fi
        done
    fi
done

if [[ $CHECK1_VIOLATIONS -eq 0 ]]; then
    echo -e "${GREEN}  ✓ No forbidden timestamps in governance paths${NC}"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 2: Missing Schema References
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 2] Validating schema references...${NC}"

REQUIRED_SCHEMAS=(
    "CHAINBRIDGE_CANONICAL_PAC_SCHEMA@v1.0.0"
    "CHAINBRIDGE_CANONICAL_WRAP_SCHEMA@v1.0.0"
    "CHAINBRIDGE_CANONICAL_BER_SCHEMA@v1.0.0"
    "RG01_SCHEMA@v1.0.0"
    "BSRG01_SCHEMA@v1.0.0"
    "AGENT_ACK_EVIDENCE_SCHEMA@v1.0.0"
)

# Check control_plane.py for schema references
CP_FILE="$PROJECT_ROOT/core/governance/control_plane.py"
if [[ -f "$CP_FILE" ]]; then
    for schema in "${REQUIRED_SCHEMAS[@]}"; do
        if ! grep -q "$schema" "$CP_FILE"; then
            echo -e "${RED}  ✗ Missing schema reference: $schema in control_plane.py${NC}"
            ((VIOLATIONS++))
        fi
    done
    if [[ $VIOLATIONS -eq 0 ]]; then
        echo -e "${GREEN}  ✓ All required schemas referenced${NC}"
    fi
else
    echo -e "${RED}  ✗ control_plane.py not found${NC}"
    ((VIOLATIONS++))
fi

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 3: BER Mandatory Fields
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 3] Validating BER mandatory fields (PAC-JEFFREY-P02R §9)...${NC}"

MANDATORY_BER_FIELDS=(
    "execution_mode"
    "execution_barrier"
    "ber_finality"
    "ledger_commit_status"
    "wrap_hash_set"
    "rg01_result"
    "bsrg01_result"
    "training_signal_digest"
    "positive_closure_digest"
)

if [[ -f "$CP_FILE" ]]; then
    # Extract BERRecord class definition
    for field in "${MANDATORY_BER_FIELDS[@]}"; do
        if ! grep -A 100 "class BERRecord:" "$CP_FILE" | head -100 | grep -q "$field"; then
            echo -e "${RED}  ✗ Missing mandatory BER field: $field${NC}"
            ((VIOLATIONS++))
        fi
    done
    if [[ $VIOLATIONS -eq 0 ]]; then
        echo -e "${GREEN}  ✓ All mandatory BER fields present${NC}"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 4: Required Classes (P02R + P03)
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 4] Validating required classes (P02R + P03)...${NC}"

REQUIRED_CLASSES=(
    # P02R classes
    "class TrainingSignal:"
    "class PositiveClosure:"
    "class AgentACKEvidence:"
    # P03 hardening classes
    "class ExecutionBarrier:"
    "class PackImmutabilityAttestation:"
    "class PositiveClosureChecklist:"
)

if [[ -f "$CP_FILE" ]]; then
    for class in "${REQUIRED_CLASSES[@]}"; do
        if ! grep -q "$class" "$CP_FILE"; then
            echo -e "${RED}  ✗ Missing required class: $class${NC}"
            ((VIOLATIONS++))
        fi
    done
    if [[ $VIOLATIONS -eq 0 ]]; then
        echo -e "${GREEN}  ✓ All P02R + P03 classes present${NC}"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 5: Provisional BER Export Blocking
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 5] Validating BER finality enforcement...${NC}"

# Check for is_settlement_eligible method
if [[ -f "$CP_FILE" ]]; then
    if grep -q "is_settlement_eligible" "$CP_FILE"; then
        # Verify it checks ber_finality == "FINAL"
        if grep -A 20 "is_settlement_eligible" "$CP_FILE" | grep -q 'ber_finality == "FINAL"'; then
            echo -e "${GREEN}  ✓ BER finality enforcement present${NC}"
        else
            echo -e "${RED}  ✗ is_settlement_eligible does not check ber_finality == FINAL${NC}"
            ((VIOLATIONS++))
        fi
    else
        echo -e "${RED}  ✗ Missing is_settlement_eligible method${NC}"
        ((VIOLATIONS++))
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 6: Invariant Documentation (P02R + P03)
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 6] Validating governance invariant documentation (P02R + P03)...${NC}"

REQUIRED_INVARIANTS=(
    # P02R invariants
    "INV-CP-009"
    "INV-CP-010"
    "INV-CP-011"
    "INV-CP-012"
    # P03 invariants
    "INV-CP-013"
    "INV-CP-014"
    "INV-CP-015"
    "INV-CP-016"
    # P04 invariants
    "INV-CP-017"
    "INV-CP-018"
    "INV-CP-019"
    "INV-CP-020"
)

if [[ -f "$CP_FILE" ]]; then
    for inv in "${REQUIRED_INVARIANTS[@]}"; do
        if ! grep -q "$inv" "$CP_FILE"; then
            echo -e "${RED}  ✗ Missing invariant documentation: $inv${NC}"
            ((VIOLATIONS++))
        fi
    done
    if [[ $VIOLATIONS -eq 0 ]]; then
        echo -e "${GREEN}  ✓ All P02R + P03 + P04 invariants documented${NC}"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 7: P03 Lane Authorization
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 7] Validating P03 lane authorization enforcement...${NC}"

if [[ -f "$CP_FILE" ]]; then
    if grep -q "validate_lane_authorization" "$CP_FILE" && grep -q "Cross-lane execution FORBIDDEN" "$CP_FILE"; then
        echo -e "${GREEN}  ✓ Lane authorization enforcement present${NC}"
    else
        echo -e "${RED}  ✗ Missing lane authorization enforcement (INV-CP-014)${NC}"
        ((VIOLATIONS++))
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 8: P04 Settlement Readiness Verdict
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 8] Validating P04 Settlement Readiness enforcement...${NC}"

# Required P04 classes
P04_CLASSES=(
    "class SettlementReadinessVerdict:"
    "class SettlementBlockingReason"
    "class SettlementReadinessStatus"
)

CHECK8_VIOLATIONS=0
if [[ -f "$CP_FILE" ]]; then
    for class in "${P04_CLASSES[@]}"; do
        if ! grep -q "$class" "$CP_FILE"; then
            echo -e "${RED}  ✗ Missing P04 class: $class${NC}"
            ((CHECK8_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for evaluate_settlement_readiness function
    if ! grep -q "def evaluate_settlement_readiness" "$CP_FILE"; then
        echo -e "${RED}  ✗ Missing evaluate_settlement_readiness function${NC}"
        ((CHECK8_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    # Check for binary status enforcement (INV-CP-018)
    if ! grep -q "ELIGIBLE\|BLOCKED" "$CP_FILE"; then
        echo -e "${RED}  ✗ Missing binary settlement status (INV-CP-018)${NC}"
        ((CHECK8_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    if [[ $CHECK8_VIOLATIONS -eq 0 ]]; then
        echo -e "${GREEN}  ✓ P04 Settlement Readiness enforcement present${NC}"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 9: P06R Lint v2 Invariant Engine
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 9] Validating P06R Lint v2 invariant engine...${NC}"

LINT_V2_FILE="$PROJECT_ROOT/core/governance/lint_v2.py"

if [[ -f "$LINT_V2_FILE" ]]; then
    CHECK9_VIOLATIONS=0
    
    # Check for invariant classes (S/M/X/T/A/F/C-INV)
    INVARIANT_CLASSES=("S_INV" "M_INV" "X_INV" "T_INV" "A_INV" "F_INV" "C_INV")
    for inv_class in "${INVARIANT_CLASSES[@]}"; do
        if ! grep -q "$inv_class" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing invariant class: $inv_class${NC}"
            ((CHECK9_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for enforcement points
    if ! grep -q "EnforcementPoint" "$LINT_V2_FILE"; then
        echo -e "${RED}  ✗ Missing EnforcementPoint enum${NC}"
        ((CHECK9_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    # Check for LintV2Engine class
    if ! grep -q "class LintV2Engine" "$LINT_V2_FILE"; then
        echo -e "${RED}  ✗ Missing LintV2Engine class${NC}"
        ((CHECK9_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    # Check for INVARIANT_REGISTRY
    if ! grep -q "INVARIANT_REGISTRY" "$LINT_V2_FILE"; then
        echo -e "${RED}  ✗ Missing INVARIANT_REGISTRY${NC}"
        ((CHECK9_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    if [[ $CHECK9_VIOLATIONS -eq 0 ]]; then
        echo -e "${GREEN}  ✓ P06R Lint v2 invariant engine present${NC}"
    fi
else
    echo -e "${RED}  ✗ lint_v2.py not found${NC}"
    ((VIOLATIONS++))
fi

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 10: P07 Runtime Activation & Agent Roster
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 10] Validating P07 runtime activation & agent roster...${NC}"

if [[ -f "$LINT_V2_FILE" ]]; then
    CHECK10_VIOLATIONS=0
    
    # Check for RuntimeActivationStatus class (P07 Block 3)
    if ! grep -q "class RuntimeActivationStatus" "$LINT_V2_FILE"; then
        echo -e "${RED}  ✗ Missing RuntimeActivationStatus class${NC}"
        ((CHECK10_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    # Check for runtime preconditions (P07 Block 3)
    RUNTIME_PRECONDITIONS=("schema_validation_enabled" "invariant_registry_loaded" "fail_closed_enabled" "runtime_admission_hook_enabled")
    for precond in "${RUNTIME_PRECONDITIONS[@]}"; do
        if ! grep -q "$precond" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing runtime precondition: $precond${NC}"
            ((CHECK10_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for AGENT_ROSTER (P07 Block 4)
    if ! grep -q "AGENT_ROSTER" "$LINT_V2_FILE"; then
        echo -e "${RED}  ✗ Missing AGENT_ROSTER${NC}"
        ((CHECK10_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    # Check for CHECKPOINT_INVARIANT_MAPPING (P07 Block 5)
    if ! grep -q "CHECKPOINT_INVARIANT_MAPPING" "$LINT_V2_FILE"; then
        echo -e "${RED}  ✗ Missing CHECKPOINT_INVARIANT_MAPPING${NC}"
        ((CHECK10_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    # Check for verify_runtime_activation method
    if ! grep -q "verify_runtime_activation" "$LINT_V2_FILE"; then
        echo -e "${RED}  ✗ Missing verify_runtime_activation method${NC}"
        ((CHECK10_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    if [[ $CHECK10_VIOLATIONS -eq 0 ]]; then
        echo -e "${GREEN}  ✓ P07 runtime activation & agent roster present${NC}"
    fi
else
    echo -e "${RED}  ✗ lint_v2.py not found${NC}"
    ((VIOLATIONS++))
fi

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════════════════════════${NC}"

if [[ $VIOLATIONS -gt 0 ]]; then
    echo -e "${RED}  GOVERNANCE LINT: FAILED${NC}"
    echo -e "${RED}  Total violations: $VIOLATIONS${NC}"
    echo -e "${RED}  Mode: FAIL_CLOSED — Build blocked${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════════════════════════${NC}"
    exit 1
else
    echo -e "${GREEN}  GOVERNANCE LINT: PASSED${NC}"
    echo -e "${GREEN}  All PAC-JEFFREY-P07 requirements satisfied${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════════════════════════${NC}"
    exit 0
fi
