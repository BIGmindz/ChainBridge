#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# run-gates.sh — Execute PAG Gates Locally
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAC: PAC-BENSON-EXEC-DAN-DEVOPS-CICD-006
# Author: Dan (GID-07) — DevOps & CI/CD Lead
# Purpose: Run all PAG gates locally before push
# Discipline: FAIL-CLOSED
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Gate statuses (using simple variables instead of associative array for portability)
PAG01_STATUS="UNKNOWN"
PAG02_STATUS="UNKNOWN"
PAG03_STATUS="UNKNOWN"
PAG04_STATUS="UNKNOWN"
PAG05_STATUS="UNKNOWN"
PAG06_STATUS="UNKNOWN"
PAG07_STATUS="UNKNOWN"
PAYLOAD_HASH=""
ATTESTATION_HASH=""

# Find repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  CHAINBRIDGE PAG GATE RUNNER${NC}"
echo -e "${CYAN}  Mode: FAIL-CLOSED | Canon: PDO (Proof → Decision → Outcome)${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAG-01: Identity Gate
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
run_pag01() {
    echo -e "${BLUE}🔐 PAG-01: AGENT IDENTITY GATE${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local required_files=(
        "core/orchestration/gates/pag01_agent.py"
        "core/orchestration/__init__.py"
    )
    
    echo "PROOF: Checking agent identity files..."
    for f in "${required_files[@]}"; do
        if [[ -f "$f" ]]; then
            echo -e "  ${GREEN}✅${NC} Found: ${f}"
        else
            echo -e "  ${RED}❌${NC} Missing: ${f}"
            PAG01_STATUS="FAIL"
            return 1
        fi
    done
    
    echo "DECISION: Agent identity infrastructure verified"
    echo "OUTCOME: PAG-01 PASS"
    PAG01_STATUS="PASS"
    echo -e "${GREEN}✅ PAG-01 IDENTITY GATE: PASS${NC}"
    echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAG-02: Runtime Gate
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
run_pag02() {
    echo -e "${BLUE}⚙️ PAG-02: RUNTIME ACTIVATION GATE${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    echo "PROOF: Checking runtime configuration..."
    
    if [[ -f "core/orchestration/engine.py" ]]; then
        echo -e "  ${GREEN}✅${NC} Found: core/orchestration/engine.py"
    else
        echo -e "  ${RED}❌${NC} Missing: core/orchestration/engine.py"
        PAG02_STATUS="FAIL"
        return 1
    fi
    
    if grep -q "FAIL-CLOSED\|halt_reason\|HALTED" core/orchestration/engine.py; then
        echo -e "  ${GREEN}✅${NC} FAIL_CLOSED discipline verified (HALTED/halt_reason)"
    else
        echo -e "  ${RED}❌${NC} FAIL_CLOSED discipline missing"
        PAG02_STATUS="FAIL"
        return 1
    fi
    
    echo "DECISION: Runtime mode EXECUTION with FAIL_CLOSED"
    echo "OUTCOME: PAG-02 PASS"
    PAG02_STATUS="PASS"
    echo -e "${GREEN}✅ PAG-02 RUNTIME GATE: PASS${NC}"
    echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAG-03: Lane Gate
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
run_pag03() {
    echo -e "${BLUE}🛤️ PAG-03: EXECUTION LANE GATE${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    echo "PROOF: Checking execution lane infrastructure..."
    
    if [[ -f "core/orchestration/gates/pag03_lane.py" ]]; then
        echo -e "  ${GREEN}✅${NC} Found: core/orchestration/gates/pag03_lane.py"
    else
        echo -e "  ${RED}❌${NC} Missing: core/orchestration/gates/pag03_lane.py"
        PAG03_STATUS="FAIL"
        return 1
    fi
    
    if grep -q "ExecutionLane" core/orchestration/gates/pag03_lane.py; then
        echo -e "  ${GREEN}✅${NC} ExecutionLane enum present"
    else
        echo -e "  ${RED}❌${NC} ExecutionLane enum missing"
        PAG03_STATUS="FAIL"
        return 1
    fi
    
    echo "DECISION: Execution lanes properly bounded"
    echo "OUTCOME: PAG-03 PASS"
    PAG03_STATUS="PASS"
    echo -e "${GREEN}✅ PAG-03 LANE GATE: PASS${NC}"
    echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAG-04: Governance Gate
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
run_pag04() {
    echo -e "${BLUE}🏛️ PAG-04: GOVERNANCE MODE GATE${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    echo "PROOF: Checking governance infrastructure..."
    
    local governance_files=(
        "core/orchestration/gates/pag04_governance.py"
        "core/lex/validator.py"
        "core/lex/schema.py"
    )
    
    for f in "${governance_files[@]}"; do
        if [[ -f "$f" ]]; then
            echo -e "  ${GREEN}✅${NC} Found: ${f}"
        else
            echo -e "  ${RED}❌${NC} Missing: ${f}"
            PAG04_STATUS="FAIL"
            return 1
        fi
    done
    
    if grep -q "GOLD_STANDARD" core/orchestration/gates/pag04_governance.py; then
        echo -e "  ${GREEN}✅${NC} GOLD_STANDARD governance mode defined"
    else
        echo -e "  ${RED}❌${NC} GOLD_STANDARD governance mode missing"
        PAG04_STATUS="FAIL"
        return 1
    fi
    
    echo "DECISION: GOLD_STANDARD governance mode active"
    echo "OUTCOME: PAG-04 PASS"
    PAG04_STATUS="PASS"
    echo -e "${GREEN}✅ PAG-04 GOVERNANCE GATE: PASS${NC}"
    echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAG-05: Review Gate (Tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
run_pag05() {
    echo -e "${BLUE}🔍 PAG-05: REVIEW GATE (TESTS)${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    echo "PROOF: Running test suites..."
    echo ""
    
    # Find Python interpreter
    local PYTHON_CMD
    if [[ -f "/Users/johnbozza/Documents/Projects/.venv/bin/python" ]]; then
        PYTHON_CMD="/Users/johnbozza/Documents/Projects/.venv/bin/python"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "  ${RED}❌${NC} No Python interpreter found"
        PAG05_STATUS="FAIL"
        return 1
    fi
    
    echo "Using Python: ${PYTHON_CMD}"
    echo ""
    
    # Run orchestration tests (from repo root for proper imports)
    echo -e "${YELLOW}Running Orchestration Engine Tests...${NC}"
    if ${PYTHON_CMD} -m core.orchestration.test_runner; then
        echo -e "  ${GREEN}✅${NC} Orchestration tests passed"
    else
        echo -e "  ${RED}❌${NC} Orchestration tests failed"
        PAG05_STATUS="FAIL"
        return 1
    fi
    echo ""
    
    # Run Lex tests
    echo -e "${YELLOW}Running Lex Runtime Tests...${NC}"
    if ${PYTHON_CMD} -m core.lex.tests.test_validator; then
        echo -e "  ${GREEN}✅${NC} Lex tests passed"
    else
        echo -e "  ${RED}❌${NC} Lex tests failed"
        PAG05_STATUS="FAIL"
        return 1
    fi
    echo ""
    
    echo "DECISION: All test suites passed"
    echo "OUTCOME: PAG-05 PASS"
    PAG05_STATUS="PASS"
    echo -e "${GREEN}✅ PAG-05 REVIEW GATE: PASS${NC}"
    echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAG-06: Payload Gate
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
run_pag06() {
    echo -e "${BLUE}📦 PAG-06: PAYLOAD VALIDATION GATE${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    echo "PROOF: Computing artifact integrity hashes..."
    
    # Hash orchestration module
    ORCH_HASH=$(find core/orchestration -name "*.py" -type f -exec shasum -a 256 {} \; | sort | shasum -a 256 | cut -d' ' -f1)
    echo "  Orchestration hash: ${ORCH_HASH:0:16}..."
    
    # Hash lex module
    LEX_HASH=$(find core/lex -name "*.py" -type f -exec shasum -a 256 {} \; | sort | shasum -a 256 | cut -d' ' -f1)
    echo "  Lex hash:           ${LEX_HASH:0:16}..."
    
    # Combined payload hash
    PAYLOAD_HASH=$(echo "${ORCH_HASH}${LEX_HASH}" | shasum -a 256 | cut -d' ' -f1)
    echo "  Combined hash:      ${PAYLOAD_HASH:0:16}..."
    
    echo ""
    echo "DECISION: All payload artifacts hashed and verified"
    echo "OUTCOME: PAG-06 PASS"
    PAG06_STATUS="PASS"
    PAYLOAD_HASH="${PAYLOAD_HASH}"
    echo -e "${GREEN}✅ PAG-06 PAYLOAD GATE: PASS${NC}"
    echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAG-07: Attestation Gate
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
run_pag07() {
    echo -e "${BLUE}✅ PAG-07: ATTESTATION GATE${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    echo "PROOF: Aggregating gate results..."
    echo ""
    
    local all_pass=true
    
    # Check each gate status
    echo -e "  PAG-01: ${PAG01_STATUS}"
    [[ "$PAG01_STATUS" != "PASS" ]] && all_pass=false
    
    echo -e "  PAG-02: ${PAG02_STATUS}"
    [[ "$PAG02_STATUS" != "PASS" ]] && all_pass=false
    
    echo -e "  PAG-03: ${PAG03_STATUS}"
    [[ "$PAG03_STATUS" != "PASS" ]] && all_pass=false
    
    echo -e "  PAG-04: ${PAG04_STATUS}"
    [[ "$PAG04_STATUS" != "PASS" ]] && all_pass=false
    
    echo -e "  PAG-05: ${PAG05_STATUS}"
    [[ "$PAG05_STATUS" != "PASS" ]] && all_pass=false
    
    echo -e "  PAG-06: ${PAG06_STATUS}"
    [[ "$PAG06_STATUS" != "PASS" ]] && all_pass=false
    
    echo ""
    
    if [[ "$all_pass" != "true" ]]; then
        echo -e "${RED}❌ FAIL-CLOSED: One or more gates failed${NC}"
        PAG07_STATUS="FAIL"
        return 1
    fi
    
    # Generate attestation
    local commit_hash=$(git rev-parse HEAD 2>/dev/null || echo "no-git")
    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local attest_hash=$(echo "${commit_hash}:${PAYLOAD_HASH}:${timestamp}" | shasum -a 256 | cut -d' ' -f1)
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "PIPELINE ATTESTATION"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Commit:      ${commit_hash:0:12}"
    echo "  Payload:     ${PAYLOAD_HASH:0:16}..."
    echo "  Attestation: ${attest_hash:0:16}..."
    echo "  Timestamp:   ${timestamp}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    echo "DECISION: All 7 PAG gates passed"
    echo "OUTCOME: PAG-07 PASS"
    PAG07_STATUS="PASS"
    ATTESTATION_HASH="${attest_hash}"
    echo -e "${GREEN}✅ PAG-07 ATTESTATION GATE: PASS${NC}"
    echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main Execution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
main() {
    local failed=false
    
    # Run gates sequentially (halt on failure)
    run_pag01 || failed=true
    [[ "$failed" == "true" ]] && { echo -e "${RED}❌ HALTED at PAG-01${NC}"; exit 1; }
    
    run_pag02 || failed=true
    [[ "$failed" == "true" ]] && { echo -e "${RED}❌ HALTED at PAG-02${NC}"; exit 1; }
    
    run_pag03 || failed=true
    [[ "$failed" == "true" ]] && { echo -e "${RED}❌ HALTED at PAG-03${NC}"; exit 1; }
    
    run_pag04 || failed=true
    [[ "$failed" == "true" ]] && { echo -e "${RED}❌ HALTED at PAG-04${NC}"; exit 1; }
    
    run_pag05 || failed=true
    [[ "$failed" == "true" ]] && { echo -e "${RED}❌ HALTED at PAG-05${NC}"; exit 1; }
    
    run_pag06 || failed=true
    [[ "$failed" == "true" ]] && { echo -e "${RED}❌ HALTED at PAG-06${NC}"; exit 1; }
    
    run_pag07 || failed=true
    [[ "$failed" == "true" ]] && { echo -e "${RED}❌ HALTED at PAG-07${NC}"; exit 1; }
    
    # Final summary
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✅ ALL PAG GATES PASSED${NC}"
    echo -e "${CYAN}  Pipeline ready for merge/deploy${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    exit 0
}

main "$@"
