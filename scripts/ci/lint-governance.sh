#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Control Plane — Governance Lint Rules
# PAC-JEFFREY-C16R: BER Formalization · P16 Agent Modularity (LAW)
# Supersedes: PAC-JEFFREY-P16 (EXECUTION OUTPUT ONLY)
# GOLD STANDARD · FAIL_CLOSED · BER FORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════════
#
# DAN (GID-07) — CI/CD Lane
#
# This script enforces PAC-JEFFREY-C16R governance requirements:
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
# 11. Validate P08 settlement engine lifecycle (INV-CP-021 through INV-CP-024)
# 12. Validate P10R platform-wide lint expansion (INV-LINT-PLAT-001 through 005)
# 13. Validate P11R Option A execution model (ACK barriers, checkpoints, WRAPs)
# 14. Validate P12 runtime determinism (8 agents, enhanced ACK, checkpoint invariants)
# 15. Validate P13 multi-agent determinism (AGENT_ACK_COLLECTION checkpoint)
# 16. Validate P14R binding settlement (LEDGER_COMMIT, BER governance invariants)
# 17. Validate P15R governance saturation (10 checkpoints, saturation scope)
# 18. Validate P16 agent modularity (8 checkpoints, agent scopes, training signals)
# 19. Validate C16R BER formalization (3 BER checkpoints, INV-BER-016-*, positive closure)
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
echo -e "${CYAN}  ChainBridge Governance Linter — PAC-JEFFREY-C16R${NC}"
echo -e "${CYAN}  FAIL_CLOSED Mode · BER FORMALIZATION${NC}"
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
# CHECK 11: P08 Settlement Engine Lifecycle
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 11] Validating P08 settlement engine lifecycle...${NC}"

SETTLEMENT_ENGINE_FILE="$PROJECT_ROOT/core/governance/settlement_engine.py"
SETTLEMENT_OC_FILE="$PROJECT_ROOT/api/settlement_oc.py"

if [[ -f "$SETTLEMENT_ENGINE_FILE" ]]; then
    CHECK11_VIOLATIONS=0
    
    # Check for SettlementEngine class
    if ! grep -q "class SettlementEngine" "$SETTLEMENT_ENGINE_FILE"; then
        echo -e "${RED}  ✗ Missing SettlementEngine class${NC}"
        ((CHECK11_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    # Check for SettlementPhase enum
    if ! grep -q "class SettlementPhase" "$SETTLEMENT_ENGINE_FILE"; then
        echo -e "${RED}  ✗ Missing SettlementPhase enum${NC}"
        ((CHECK11_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    # Check for P08 invariants (INV-CP-021 through INV-CP-024)
    P08_INVARIANTS=("INV-CP-021" "INV-CP-022" "INV-CP-023" "INV-CP-024")
    for inv in "${P08_INVARIANTS[@]}"; do
        if ! grep -q "$inv" "$SETTLEMENT_ENGINE_FILE"; then
            echo -e "${RED}  ✗ Missing P08 invariant: $inv${NC}"
            ((CHECK11_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for lifecycle phases
    LIFECYCLE_PHASES=("PDO_RECEIVED" "READINESS_ELIGIBLE" "LEDGER_COMMITTED" "FINALITY_ATTESTED" "SETTLEMENT_COMPLETE")
    for phase in "${LIFECYCLE_PHASES[@]}"; do
        if ! grep -q "$phase" "$SETTLEMENT_ENGINE_FILE"; then
            echo -e "${RED}  ✗ Missing lifecycle phase: $phase${NC}"
            ((CHECK11_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for FinalityAttestation class
    if ! grep -q "class FinalityAttestation" "$SETTLEMENT_ENGINE_FILE"; then
        echo -e "${RED}  ✗ Missing FinalityAttestation class${NC}"
        ((CHECK11_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    # Check for LedgerCommitResult class
    if ! grep -q "class LedgerCommitResult" "$SETTLEMENT_ENGINE_FILE"; then
        echo -e "${RED}  ✗ Missing LedgerCommitResult class${NC}"
        ((CHECK11_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    if [[ $CHECK11_VIOLATIONS -eq 0 ]]; then
        echo -e "${GREEN}  ✓ P08 settlement engine lifecycle present${NC}"
    fi
else
    echo -e "${RED}  ✗ settlement_engine.py not found${NC}"
    ((VIOLATIONS++))
fi

# Check for Settlement OC API
if [[ -f "$SETTLEMENT_OC_FILE" ]]; then
    if ! grep -q "router = APIRouter" "$SETTLEMENT_OC_FILE"; then
        echo -e "${RED}  ✗ Settlement OC router not configured${NC}"
        ((VIOLATIONS++))
    else
        echo -e "${GREEN}  ✓ Settlement OC API present${NC}"
    fi
else
    echo -e "${RED}  ✗ settlement_oc.py not found${NC}"
    ((VIOLATIONS++))
fi

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 12: P10R Platform-Wide Lint v2 Expansion
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 12] Validating P10R platform-wide lint expansion...${NC}"

if [[ -f "$LINT_V2_FILE" ]]; then
    CHECK12_VIOLATIONS=0
    
    # Check for P10R platform invariants (INV-LINT-PLAT-001 through 005)
    P10R_INVARIANTS=("INV-LINT-PLAT-001" "INV-LINT-PLAT-002" "INV-LINT-PLAT-003" "INV-LINT-PLAT-004" "INV-LINT-PLAT-005")
    for inv in "${P10R_INVARIANTS[@]}"; do
        if ! grep -q "$inv" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P10R platform invariant: $inv${NC}"
            ((CHECK12_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for expanded checkpoints (10 checkpoints per P10R Block 5)
    P10R_CHECKPOINTS=("RUNTIME_ACTIVATION" "AGENT_ACK_COLLECTION" "AGENT_EXECUTION" "API_ADMISSION" "UI_RENDER_VALIDATION" "LEDGER_COMMIT" "FINALITY_SEAL")
    for checkpoint in "${P10R_CHECKPOINTS[@]}"; do
        if ! grep -q "$checkpoint" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P10R checkpoint: $checkpoint${NC}"
            ((CHECK12_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for ALEX agent (GID-08) in canonical registry or lint_v2.py
    GID_REGISTRY_FILE="$PROJECT_ROOT/core/governance/gid_registry.json"
    if [[ -f "$GID_REGISTRY_FILE" ]]; then
        if ! grep -q '"GID-08"' "$GID_REGISTRY_FILE"; then
            echo -e "${RED}  ✗ Missing ALEX (GID-08) in canonical registry${NC}"
            ((CHECK12_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    elif ! grep -q "GID-08" "$LINT_V2_FILE"; then
        echo -e "${RED}  ✗ Missing ALEX (GID-08) in agent roster${NC}"
        ((CHECK12_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    if [[ $CHECK12_VIOLATIONS -eq 0 ]]; then
        echo -e "${GREEN}  ✓ P10R platform-wide lint expansion present${NC}"
    fi
else
    echo -e "${RED}  ✗ lint_v2.py not found${NC}"
    ((VIOLATIONS++))
fi

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 13: P11R Option A Execution Model
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 13] Validating P11R Option A execution model...${NC}"

if [[ -f "$LINT_V2_FILE" ]]; then
    CHECK13_VIOLATIONS=0
    
    # Check for P11R execution model components
    P11R_COMPONENTS=("P11RExecutionModel" "P11RBarrierType" "P11RBarrierRelease" "RuntimeActivationACK" "AgentActivationACK" "P11RAgentACKBarrier" "P11RCheckpointTracker" "P11R_CHECKPOINT_SEQUENCE" "P11RWrapRequirement" "P11R_REQUIRED_WRAPS" "P11RBERClassification" "P11RBERStatus" "P11RExecutionState")
    for component in "${P11R_COMPONENTS[@]}"; do
        if ! grep -q "$component" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P11R component: $component${NC}"
            ((CHECK13_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for P11R checkpoint sequence (8 checkpoints per Block 5)
    P11R_CHECKPOINTS=("PAC_ADMISSION" "RUNTIME_ACTIVATION" "RUNTIME_ACK_COLLECTION" "AGENT_ACTIVATION" "AGENT_ACK_COLLECTION" "AGENT_EXECUTION" "REVIEW_GATES" "BER_ELIGIBILITY")
    for checkpoint in "${P11R_CHECKPOINTS[@]}"; do
        if ! grep -q "$checkpoint" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P11R checkpoint: $checkpoint${NC}"
            ((CHECK13_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for P11R activated agents (7 agents per Block 4)
    P11R_AGENTS=("GID-00" "GID-01" "GID-02" "GID-07" "GID-06" "GID-11" "GID-08")
    for agent in "${P11R_AGENTS[@]}"; do
        if ! grep -q "$agent" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P11R agent: $agent${NC}"
            ((CHECK13_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for P11R BER PROVISIONAL classification
    if ! grep -q "PROVISIONAL" "$LINT_V2_FILE"; then
        echo -e "${RED}  ✗ Missing P11R BER PROVISIONAL classification${NC}"
        ((CHECK13_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    if [[ $CHECK13_VIOLATIONS -eq 0 ]]; then
        echo -e "${GREEN}  ✓ P11R Option A execution model present${NC}"
    fi
else
    echo -e "${RED}  ✗ lint_v2.py not found${NC}"
    ((VIOLATIONS++))
fi

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 14: P12 Platform-Wide Runtime Determinism
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 14] Validating P12 platform-wide runtime determinism...${NC}"

if [[ -f "$LINT_V2_FILE" ]]; then
    CHECK14_VIOLATIONS=0
    
    # Check for P12 components (enhanced over P11R)
    P12_COMPONENTS=("P12_CHECKPOINT_SEQUENCE" "P12_CHECKPOINT_INVARIANT_MAPPING" "P12_REQUIRED_WRAPS" "P12_ACTIVATED_AGENTS" "P12_AGENT_SCOPES" "compute_evidence_hash" "latency_ms" "authorization_scope" "evidence_hash")
    for component in "${P12_COMPONENTS[@]}"; do
        if ! grep -q "$component" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P12 component: $component${NC}"
            ((CHECK14_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for P12 checkpoint → invariant mappings (8 checkpoints per Block 6)
    P12_CHECKPOINTS=("PAC_ADMISSION" "RUNTIME_ACTIVATION" "RUNTIME_ACK" "AGENT_ACTIVATION" "AGENT_EXECUTION" "REVIEW_GATES" "BER_ELIGIBILITY" "FINALITY_SEAL")
    for checkpoint in "${P12_CHECKPOINTS[@]}"; do
        if ! grep -q "$checkpoint" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P12 checkpoint: $checkpoint${NC}"
            ((CHECK14_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for P12 activated agents (8 agents per Block 4 — includes PAX GID-05)
    P12_AGENTS=("GID-00" "GID-01" "GID-02" "GID-07" "GID-06" "GID-11" "GID-08" "GID-05")
    for agent in "${P12_AGENTS[@]}"; do
        if ! grep -q "$agent" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P12 agent: $agent${NC}"
            ((CHECK14_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for PAX WRAP (new in P12)
    if ! grep -q "WRAP-PAX-GID05-PAC-JEFFREY-P12" "$LINT_V2_FILE"; then
        echo -e "${RED}  ✗ Missing P12 PAX WRAP: WRAP-PAX-GID05-PAC-JEFFREY-P12${NC}"
        ((CHECK14_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    # Check for P12 invariant classes in checkpoint mapping
    P12_INV_CLASSES=("S-INV" "M-INV" "X-INV" "T-INV" "A-INV" "F-INV" "C-INV")
    for inv_class in "${P12_INV_CLASSES[@]}"; do
        if ! grep -q "$inv_class" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P12 invariant class: $inv_class${NC}"
            ((CHECK14_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for AGENT_ACK_EVIDENCE_SCHEMA reference
    if ! grep -q "AGENT_ACK_EVIDENCE_SCHEMA" "$LINT_V2_FILE"; then
        echo -e "${RED}  ✗ Missing AGENT_ACK_EVIDENCE_SCHEMA reference${NC}"
        ((CHECK14_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    if [[ $CHECK14_VIOLATIONS -eq 0 ]]; then
        echo -e "${GREEN}  ✓ P12 platform-wide runtime determinism validated${NC}"
    fi
else
    echo -e "${RED}  ✗ lint_v2.py not found${NC}"
    ((VIOLATIONS++))
fi

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 15: P13 Multi-Agent Determinism
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 15] Validating P13 multi-agent determinism...${NC}"

if [[ -f "$LINT_V2_FILE" ]]; then
    CHECK15_VIOLATIONS=0
    
    # Check for P13 components
    P13_COMPONENTS=("P13_CHECKPOINT_SEQUENCE" "P13_CHECKPOINT_INVARIANT_MAPPING" "P13_REQUIRED_WRAPS" "P13_ACTIVATED_AGENTS" "get_p13_required_invariants" "validate_p13_checkpoint_invariants")
    for component in "${P13_COMPONENTS[@]}"; do
        if ! grep -q "$component" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P13 component: $component${NC}"
            ((CHECK15_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for P13 AGENT_ACK_COLLECTION checkpoint (key P13 addition)
    if ! grep -q "AGENT_ACK_COLLECTION" "$LINT_V2_FILE"; then
        echo -e "${RED}  ✗ Missing P13 AGENT_ACK_COLLECTION checkpoint${NC}"
        ((CHECK15_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    # Check for P13 WRAPs (8 agents)
    P13_WRAPS=("WRAP-BENSON-GID00-PAC-JEFFREY-P13" "WRAP-CODY-GID01-PAC-JEFFREY-P13" "WRAP-SONNY-GID02-PAC-JEFFREY-P13" "WRAP-DAN-GID07-PAC-JEFFREY-P13" "WRAP-SAM-GID06-PAC-JEFFREY-P13" "WRAP-ATLAS-GID11-PAC-JEFFREY-P13" "WRAP-ALEX-GID08-PAC-JEFFREY-P13" "WRAP-PAX-GID05-PAC-JEFFREY-P13")
    for wrap in "${P13_WRAPS[@]}"; do
        if ! grep -q "$wrap" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P13 WRAP: $wrap${NC}"
            ((CHECK15_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    if [[ $CHECK15_VIOLATIONS -eq 0 ]]; then
        echo -e "${GREEN}  ✓ P13 multi-agent determinism validated${NC}"
    fi
else
    echo -e "${RED}  ✗ lint_v2.py not found${NC}"
    ((VIOLATIONS++))
fi

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 16: P14R Binding Settlement
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 16] Validating P14R binding settlement...${NC}"

if [[ -f "$LINT_V2_FILE" ]]; then
    CHECK16_VIOLATIONS=0
    
    # Check for P14R components
    P14R_COMPONENTS=("P14R_CHECKPOINT_SEQUENCE" "P14R_CHECKPOINT_INVARIANT_MAPPING" "P14R_BER_GOVERNANCE_INVARIANTS" "P14R_REQUIRED_WRAPS" "P14R_ACTIVATED_AGENTS" "P14RBERClassification" "P14RBERStatus" "get_p14r_required_invariants" "validate_p14r_checkpoint_invariants")
    for component in "${P14R_COMPONENTS[@]}"; do
        if ! grep -q "$component" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P14R component: $component${NC}"
            ((CHECK16_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for LEDGER_COMMIT checkpoint (key P14R addition for binding settlement)
    if ! grep -q "LEDGER_COMMIT" "$LINT_V2_FILE"; then
        echo -e "${RED}  ✗ Missing P14R LEDGER_COMMIT checkpoint${NC}"
        ((CHECK16_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    # Check for P14R BER governance invariants (Block 6)
    P14R_BER_INVS=("INV-BER-001" "INV-BER-002" "INV-BER-003" "INV-BER-004" "INV-BER-005" "INV-BER-006")
    for inv in "${P14R_BER_INVS[@]}"; do
        if ! grep -q "$inv" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P14R BER invariant: $inv${NC}"
            ((CHECK16_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for P14R WRAPs (8 agents)
    P14R_WRAPS=("WRAP-BENSON-GID00-PAC-JEFFREY-P14R" "WRAP-CODY-GID01-PAC-JEFFREY-P14R" "WRAP-SONNY-GID02-PAC-JEFFREY-P14R" "WRAP-DAN-GID07-PAC-JEFFREY-P14R" "WRAP-SAM-GID06-PAC-JEFFREY-P14R" "WRAP-ATLAS-GID11-PAC-JEFFREY-P14R" "WRAP-ALEX-GID08-PAC-JEFFREY-P14R" "WRAP-PAX-GID05-PAC-JEFFREY-P14R")
    for wrap in "${P14R_WRAPS[@]}"; do
        if ! grep -q "$wrap" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P14R WRAP: $wrap${NC}"
            ((CHECK16_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for binding settlement indicators
    if ! grep -q "execution_binding.*True" "$LINT_V2_FILE"; then
        echo -e "${RED}  ✗ Missing P14R execution_binding = True${NC}"
        ((CHECK16_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    if ! grep -q "settlement_effect.*BINDING" "$LINT_V2_FILE"; then
        echo -e "${RED}  ✗ Missing P14R settlement_effect = BINDING${NC}"
        ((CHECK16_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    if [[ $CHECK16_VIOLATIONS -eq 0 ]]; then
        echo -e "${GREEN}  ✓ P14R binding settlement validated${NC}"
    fi
else
    echo -e "${RED}  ✗ lint_v2.py not found${NC}"
    ((VIOLATIONS++))
fi

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 17: P15R Governance Saturation
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 17] Validating P15R governance saturation...${NC}"

if [[ -f "$LINT_V2_FILE" ]]; then
    CHECK17_VIOLATIONS=0
    
    # Check for P15R components
    P15R_COMPONENTS=("P15R_CHECKPOINT_SEQUENCE" "P15R_CHECKPOINT_INVARIANT_MAPPING" "P15R_GOVERNANCE_SATURATION_SCOPE" "P15R_RUNTIME_ACTIVATION_REQUIREMENTS" "P15R_REQUIRED_WRAPS" "P15R_ACTIVATED_AGENTS" "get_p15r_required_invariants" "validate_p15r_checkpoint_invariants" "validate_p15r_governance_saturation")
    for component in "${P15R_COMPONENTS[@]}"; do
        if ! grep -q "$component" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P15R component: $component${NC}"
            ((CHECK17_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for P15R 10 checkpoints
    P15R_CHECKPOINTS=("PAC_ADMISSION" "RUNTIME_ACTIVATION" "RUNTIME_ACK_COLLECTION" "AGENT_ACTIVATION" "AGENT_ACK_COLLECTION" "AGENT_EXECUTION" "REVIEW_GATES" "BER_ELIGIBILITY" "LEDGER_COMMIT" "FINALITY_SEAL")
    for checkpoint in "${P15R_CHECKPOINTS[@]}"; do
        if ! grep -q "$checkpoint" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P15R checkpoint: $checkpoint${NC}"
            ((CHECK17_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for P15R governance saturation scope
    P15R_SCOPES=("control_plane" "governance_engine" "lint_v2_compiler" "runtime_admission" "operator_console" "api_routers" "ber_settlement")
    for scope in "${P15R_SCOPES[@]}"; do
        if ! grep -q "$scope" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P15R saturation scope: $scope${NC}"
            ((CHECK17_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for P15R runtime activation requirements
    P15R_RUNTIME_REQS=("lint_v2_compiler_active" "agent_ack_enforced")
    for req in "${P15R_RUNTIME_REQS[@]}"; do
        if ! grep -q "$req" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P15R runtime requirement: $req${NC}"
            ((CHECK17_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for P15R WRAPs (8 agents)
    P15R_WRAPS=("WRAP-BENSON-GID00-PAC-JEFFREY-P15R" "WRAP-CODY-GID01-PAC-JEFFREY-P15R" "WRAP-SONNY-GID02-PAC-JEFFREY-P15R" "WRAP-DAN-GID07-PAC-JEFFREY-P15R" "WRAP-SAM-GID06-PAC-JEFFREY-P15R" "WRAP-ATLAS-GID11-PAC-JEFFREY-P15R" "WRAP-ALEX-GID08-PAC-JEFFREY-P15R" "WRAP-PAX-GID05-PAC-JEFFREY-P15R")
    for wrap in "${P15R_WRAPS[@]}"; do
        if ! grep -q "$wrap" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P15R WRAP: $wrap${NC}"
            ((CHECK17_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    if [[ $CHECK17_VIOLATIONS -eq 0 ]]; then
        echo -e "${GREEN}  ✓ P15R governance saturation validated${NC}"
    fi
else
    echo -e "${RED}  ✗ lint_v2.py not found${NC}"
    ((VIOLATIONS++))
fi

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 18: P16 Agent Modularity & Uniformization
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 18] Validating P16 agent modularity & uniformization...${NC}"

if [[ -f "$LINT_V2_FILE" ]]; then
    CHECK18_VIOLATIONS=0
    
    # Check for P16 components
    P16_COMPONENTS=("P16_CHECKPOINT_SEQUENCE" "P16_CHECKPOINT_INVARIANT_MAPPING" "P16_AGENT_SCOPES" "P16_TRAINING_SIGNALS" "P16_MODULARITY_INVARIANTS" "P16_REQUIRED_WRAPS" "P16_ACTIVATED_AGENTS" "get_p16_required_invariants" "validate_p16_checkpoint_invariants" "validate_p16_agent_modularity")
    for component in "${P16_COMPONENTS[@]}"; do
        if ! grep -q "$component" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P16 component: $component${NC}"
            ((CHECK18_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for P16 8 checkpoints (returns to simpler sequence)
    P16_CHECKPOINTS=("PAC_ADMISSION" "RUNTIME_ACTIVATION" "RUNTIME_ACK" "AGENT_ACTIVATION" "AGENT_ACK_COLLECTION" "AGENT_EXECUTION" "REVIEW_GATES" "BER_ELIGIBILITY")
    for checkpoint in "${P16_CHECKPOINTS[@]}"; do
        if ! grep -q "$checkpoint" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P16 checkpoint: $checkpoint${NC}"
            ((CHECK18_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for P16 agent scopes (canonical agent uniform)
    P16_SCOPES=("execution_control" "system_primitives" "oc_surfaces" "pipeline_gates" "threat_controls" "hygiene" "law_invariants" "constraint_modeling")
    for scope in "${P16_SCOPES[@]}"; do
        if ! grep -q "$scope" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P16 agent scope: $scope${NC}"
            ((CHECK18_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for P16 training signals (Block 9)
    P16_SIGNALS=("TS-P16-001" "TS-P16-002")
    for signal in "${P16_SIGNALS[@]}"; do
        if ! grep -q "$signal" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P16 training signal: $signal${NC}"
            ((CHECK18_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for P16 modularity invariants (Block 1)
    P16_MOD_INVS=("INV-MOD-001" "INV-MOD-002" "INV-MOD-003" "INV-MOD-004" "INV-MOD-005")
    for inv in "${P16_MOD_INVS[@]}"; do
        if ! grep -q "$inv" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P16 modularity invariant: $inv${NC}"
            ((CHECK18_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for P16 WRAPs (8 agents)
    P16_WRAPS=("WRAP-BENSON-GID00-PAC-JEFFREY-P16" "WRAP-CODY-GID01-PAC-JEFFREY-P16" "WRAP-SONNY-GID02-PAC-JEFFREY-P16" "WRAP-DAN-GID07-PAC-JEFFREY-P16" "WRAP-SAM-GID06-PAC-JEFFREY-P16" "WRAP-ATLAS-GID11-PAC-JEFFREY-P16" "WRAP-ALEX-GID08-PAC-JEFFREY-P16" "WRAP-PAX-GID05-PAC-JEFFREY-P16")
    for wrap in "${P16_WRAPS[@]}"; do
        if ! grep -q "$wrap" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing P16 WRAP: $wrap${NC}"
            ((CHECK18_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    if [[ $CHECK18_VIOLATIONS -eq 0 ]]; then
        echo -e "${GREEN}  ✓ P16 agent modularity & uniformization validated${NC}"
    fi
else
    echo -e "${RED}  ✗ lint_v2.py not found${NC}"
    ((VIOLATIONS++))
fi

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 19: C16R BER Formalization
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}[CHECK 19] Validating C16R BER formalization...${NC}"

if [[ -f "$LINT_V2_FILE" ]]; then
    CHECK19_VIOLATIONS=0
    
    # Check for C16R components
    C16R_COMPONENTS=("C16R_CHECKPOINT_SEQUENCE" "C16R_CHECKPOINT_INVARIANT_MAPPING" "C16R_BER_GOVERNANCE_INVARIANTS" "C16R_REQUIRED_WRAPS" "C16R_ACTIVATED_AGENTS" "C16R_REVIEW_GATES" "C16R_TRAINING_SIGNALS" "C16R_POSITIVE_CLOSURE" "C16RBERFinality" "get_c16r_required_invariants" "validate_c16r_checkpoint_invariants" "validate_c16r_positive_closure")
    for component in "${C16R_COMPONENTS[@]}"; do
        if ! grep -q "$component" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing C16R component: $component${NC}"
            ((CHECK19_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for C16R 3 BER checkpoints
    C16R_CHECKPOINTS=("BER_ADMISSION" "BER_REVIEW" "BER_FINALITY")
    for checkpoint in "${C16R_CHECKPOINTS[@]}"; do
        if ! grep -q "$checkpoint" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing C16R checkpoint: $checkpoint${NC}"
            ((CHECK19_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for C16R BER governance invariants (Block 6)
    C16R_BER_INVS=("INV-BER-016-01" "INV-BER-016-02" "INV-BER-016-03" "INV-BER-016-04" "INV-BER-016-05" "INV-BER-016-06" "INV-BER-016-07")
    for inv in "${C16R_BER_INVS[@]}"; do
        if ! grep -q "$inv" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing C16R BER invariant: $inv${NC}"
            ((CHECK19_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for C16R WRAPs (2 agents - NON_EXECUTING)
    C16R_WRAPS=("WRAP-BENSON-GID00-PAC-JEFFREY-C16R" "WRAP-ALEX-GID08-PAC-JEFFREY-C16R")
    for wrap in "${C16R_WRAPS[@]}"; do
        if ! grep -q "$wrap" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing C16R WRAP: $wrap${NC}"
            ((CHECK19_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for C16R training signal
    if ! grep -q "TS-C16R-001" "$LINT_V2_FILE"; then
        echo -e "${RED}  ✗ Missing C16R training signal: TS-C16R-001${NC}"
        ((CHECK19_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    # Check for C16R positive closure requirements
    C16R_CLOSURE=("pac_received" "all_blocks_present" "no_execution_performed" "ber_formalized" "zero_drift_confirmed")
    for closure in "${C16R_CLOSURE[@]}"; do
        if ! grep -q "$closure" "$LINT_V2_FILE"; then
            echo -e "${RED}  ✗ Missing C16R positive closure: $closure${NC}"
            ((CHECK19_VIOLATIONS++))
            ((VIOLATIONS++))
        fi
    done
    
    # Check for BER-PAC-JEFFREY-P16 formalization
    if ! grep -q "BER-PAC-JEFFREY-P16" "$LINT_V2_FILE"; then
        echo -e "${RED}  ✗ Missing BER-PAC-JEFFREY-P16 formalization${NC}"
        ((CHECK19_VIOLATIONS++))
        ((VIOLATIONS++))
    fi
    
    if [[ $CHECK19_VIOLATIONS -eq 0 ]]; then
        echo -e "${GREEN}  ✓ C16R BER formalization validated${NC}"
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
    echo -e "${GREEN}  All PAC-JEFFREY-C16R requirements satisfied${NC}"
    echo -e "${GREEN}  BER FORMALIZATION COMPLETE${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════════════════════════${NC}"
    exit 0
fi
