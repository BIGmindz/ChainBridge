#!/bin/bash
# IG Node Entrypoint Script
# PAC-INFRA-P1502: IG Node Infrastructure Build & Deployment
#
# CLASSIFICATION: LAW-tier (Judicial Enforcement)
# AUTHORITY: DAN [GID-07] + SAM [GID-06]
# VERSION: 1.0.0
# DATE: 2026-01-25
#
# PURPOSE: Orchestrate OPA + Envoy + Health Server for IG Node
# PATTERN: Fail-closed (any failure → exit 1, prevent agent startup)

set -euo pipefail

# ============================================================================
# Logging functions
# ============================================================================
log() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [IG-NODE] [INFO] $*" | tee -a /var/log/ig/ig-node.log
}

log_error() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [IG-NODE] [ERROR] $*" | tee -a /var/log/ig/ig-node.log >&2
}

log_warn() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [IG-NODE] [WARN] $*" | tee -a /var/log/ig/ig-node.log
}

# ============================================================================
# Startup banner
# ============================================================================
log "=========================================="
log "ChainBridge Digital Inspector General"
log "GID-12: Independent Judiciary"
log "Version: ${IG_NODE_VERSION}"
log "Mode: ${IG_MODE}"
log "=========================================="

# ============================================================================
# Preflight checks
# ============================================================================
log "Running preflight checks..."

# Check OPA binary
if ! command -v opa &> /dev/null; then
    log_error "OPA binary not found"
    exit 1
fi
log "✓ OPA binary: $(opa version | head -n 1)"

# Check Envoy binary
if ! command -v envoy &> /dev/null; then
    log_error "Envoy binary not found"
    exit 1
fi
log "✓ Envoy binary: $(envoy --version | head -n 1)"

# Check policy directory
if [ ! -d "${OPA_POLICY_DIR}" ]; then
    log_error "OPA policy directory not found: ${OPA_POLICY_DIR}"
    exit 1
fi

POLICY_COUNT=$(find "${OPA_POLICY_DIR}" -name "*.rego" | wc -l)
log "✓ OPA policies found: ${POLICY_COUNT} .rego files"

if [ "${POLICY_COUNT}" -eq 0 ]; then
    log_warn "No OPA policies found. Default deny will be enforced."
fi

# Check Envoy configuration
if [ ! -f "/etc/envoy/envoy.yaml" ]; then
    log_error "Envoy configuration not found: /etc/envoy/envoy.yaml"
    exit 1
fi
log "✓ Envoy configuration found"

# Check database connectivity (epistemic independence)
log "Testing database connectivity (epistemic independence)..."
if command -v nc &> /dev/null; then
    if nc -zv "${POSTGRES_HOST}" "${POSTGRES_PORT}" 2>&1 | grep -q succeeded; then
        log "✓ Database reachable: ${POSTGRES_HOST}:${POSTGRES_PORT}"
    else
        log_warn "Database not reachable (may not be started yet)"
    fi
else
    log_warn "netcat not available, skipping DB connectivity check"
fi

# Check SXS Ledger connectivity
log "Testing SXS Ledger connectivity..."
if curl -f -s "${SXS_LEDGER_URL}/health" > /dev/null 2>&1; then
    log "✓ SXS Ledger reachable: ${SXS_LEDGER_URL}"
else
    log_warn "SXS Ledger not reachable (may not be started yet)"
fi

log "Preflight checks complete"

# ============================================================================
# Start OPA server (background process)
# ============================================================================
log "=========================================="
log "Starting OPA policy engine..."
log "=========================================="

OPA_LOG_FILE="/var/log/ig/opa.log"

opa run --server \
    --addr="${OPA_ADDR}" \
    --diagnostic-addr="${OPA_DIAGNOSTIC_ADDR}" \
    --bundle="${OPA_POLICY_DIR}" \
    --watch \
    --log-level=info \
    --log-format=json \
    > "${OPA_LOG_FILE}" 2>&1 &

OPA_PID=$!
log "OPA started (PID: ${OPA_PID})"
log "OPA API: http://${OPA_ADDR}"
log "OPA Diagnostics: http://${OPA_DIAGNOSTIC_ADDR}"

# Wait for OPA to be ready
log "Waiting for OPA to be ready..."
for i in {1..30}; do
    if curl -f -s "http://${OPA_ADDR}/health" > /dev/null 2>&1; then
        log "✓ OPA is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "OPA failed to start within 30 seconds"
        kill "${OPA_PID}" 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# ============================================================================
# Start Envoy proxy (background process)
# ============================================================================
log "=========================================="
log "Starting Envoy HTTP proxy..."
log "=========================================="

ENVOY_LOG_FILE="/var/log/ig/envoy.log"

envoy -c /etc/envoy/envoy.yaml \
    --log-level info \
    --log-format '[%Y-%m-%d %T.%e][%t][%l][%n] %v' \
    > "${ENVOY_LOG_FILE}" 2>&1 &

ENVOY_PID=$!
log "Envoy started (PID: ${ENVOY_PID})"
log "Envoy Proxy: http://localhost:${ENVOY_PROXY_PORT}"
log "Envoy Admin: http://localhost:${ENVOY_ADMIN_PORT}"

# Wait for Envoy to be ready
log "Waiting for Envoy to be ready..."
for i in {1..30}; do
    if curl -f -s "http://localhost:${ENVOY_ADMIN_PORT}/ready" > /dev/null 2>&1; then
        log "✓ Envoy is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "Envoy failed to start within 30 seconds"
        kill "${OPA_PID}" "${ENVOY_PID}" 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# ============================================================================
# Start health check server (Python, foreground)
# ============================================================================
log "=========================================="
log "Starting health check server..."
log "=========================================="

# Health server will run in foreground and keep container alive
python3 /app/ig-node/health_server.py &
HEALTH_PID=$!
log "Health server started (PID: ${HEALTH_PID})"
log "Health endpoint: http://localhost:9999/health"

# ============================================================================
# Monitor processes (fail-closed: if any dies, kill all and exit)
# ============================================================================
log "=========================================="
log "IG Node fully operational"
log "Monitoring processes (fail-closed enforcement)..."
log "=========================================="

# Trap signals for graceful shutdown
shutdown() {
    log "=========================================="
    log "Shutdown signal received"
    log "=========================================="
    log "Stopping OPA (PID: ${OPA_PID})..."
    kill "${OPA_PID}" 2>/dev/null || true
    log "Stopping Envoy (PID: ${ENVOY_PID})..."
    kill "${ENVOY_PID}" 2>/dev/null || true
    log "Stopping health server (PID: ${HEALTH_PID})..."
    kill "${HEALTH_PID}" 2>/dev/null || true
    log "IG Node shutdown complete"
    exit 0
}

trap shutdown SIGTERM SIGINT

# Monitor loop (check every 5 seconds)
while true; do
    # Check if OPA is still running
    if ! kill -0 "${OPA_PID}" 2>/dev/null; then
        log_error "OPA process died unexpectedly (PID: ${OPA_PID})"
        log_error "FAIL-CLOSED: Terminating IG Node"
        kill "${ENVOY_PID}" "${HEALTH_PID}" 2>/dev/null || true
        exit 1
    fi
    
    # Check if Envoy is still running
    if ! kill -0 "${ENVOY_PID}" 2>/dev/null; then
        log_error "Envoy process died unexpectedly (PID: ${ENVOY_PID})"
        log_error "FAIL-CLOSED: Terminating IG Node"
        kill "${OPA_PID}" "${HEALTH_PID}" 2>/dev/null || true
        exit 1
    fi
    
    # Check if health server is still running
    if ! kill -0 "${HEALTH_PID}" 2>/dev/null; then
        log_error "Health server died unexpectedly (PID: ${HEALTH_PID})"
        log_error "FAIL-CLOSED: Terminating IG Node"
        kill "${OPA_PID}" "${ENVOY_PID}" 2>/dev/null || true
        exit 1
    fi
    
    sleep 5
done

# ============================================================================
# Constitutional Attestation
# ============================================================================
# "This script orchestrates the Digital Inspector General. If any component
# fails (OPA, Envoy, health server), the entire IG Node fails (fail-closed).
# Agent containers depend on IG Node health. If IG fails, agents cannot start.
# This enforces I-GOV-007: No Action without IG Sign-off."
#
# — DAN [GID-07], Infrastructure & Docker Specialist
# ============================================================================
