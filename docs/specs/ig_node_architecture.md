# IG Node Sidecar Architecture Specification

**PAC-GOV-P1501: Digital Inspector General Implementation**  
**COMPONENT:** IG Node (Inspector General Sidecar Container)  
**PATTERN:** Simplex Architecture for Safety-Critical Systems  
**AUTHORITY:** JEFFREY [GID-CONST-01] + CINDY [GID-04]  
**VERSION:** 1.0.0  
**DATE:** 2026-01-25

---

## 1. Architecture Overview

The **IG Node** is a **sidecar container** that intercepts all agent traffic using the **Simplex Architecture** pattern for safety-critical systems.

**Simplex Pattern:**
- **Primary Channel:** Agent → Action (optimized for functionality)
- **Safety Channel:** IG Node → Veto/Allow (optimized for compliance)
- **Decision Rule:** Safety channel **overrides** primary channel (fail-closed)

**Proven Applications:**
- Aircraft autopilot (safety pilot override)
- Nuclear reactor SCRAM (emergency shutdown)
- Autonomous vehicles (safety driver takeover)

**ChainBridge Application:** Multi-agent AI governance with constitutional oversight

---

## 2. Container Topology

### 2.1 Kubernetes Pod Layout

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: chainbridge-agent-pod
  namespace: chainbridge
  labels:
    app: chainbridge
    component: agent-pod
    oversight: ig-enforced
spec:
  # ========================================
  # CONTAINER 1: Agent Container
  # ========================================
  containers:
  - name: agent-container
    image: chainbridge/agent:v1.0.0
    env:
      # Force all HTTP traffic through IG proxy
      - name: HTTP_PROXY
        value: "http://localhost:9999"
      - name: HTTPS_PROXY
        value: "http://localhost:9999"
      - name: NO_PROXY
        value: "localhost,127.0.0.1"
      
      # Force all DB connections through IG proxy
      - name: DATABASE_URL
        value: "postgresql://localhost:5433/chainbridge"
      
      # IG enforcement flag
      - name: IG_ENFORCEMENT
        value: "true"
    
    # Read-only filesystem (writes require IG approval via FUSE)
    securityContext:
      readOnlyRootFilesystem: true
      runAsNonRoot: true
      runAsUser: 1000
      capabilities:
        drop:
          - ALL
    
    # Shared volumes with IG Node
    volumeMounts:
      - name: writable-tmp
        mountPath: /tmp
      - name: ig-fuse-overlay
        mountPath: /app/writable
    
    resources:
      limits:
        cpu: "2"
        memory: "4Gi"
      requests:
        cpu: "1"
        memory: "2Gi"
  
  # ========================================
  # CONTAINER 2: IG Node (Sidecar)
  # ========================================
  - name: ig-node
    image: chainbridge/ig-node:v1.0.0
    env:
      # Direct DB access (epistemic independence)
      - name: POSTGRES_HOST
        value: "postgres.chainbridge.svc.cluster.local"
      - name: POSTGRES_PORT
        value: "5432"
      - name: POSTGRES_DB
        value: "chainbridge"
      - name: POSTGRES_USER
        valueFrom:
          secretKeyRef:
            name: ig-node-db-secret
            key: username
      - name: POSTGRES_PASSWORD
        valueFrom:
          secretKeyRef:
            name: ig-node-db-secret
            key: password
      
      # OPA policy directory
      - name: OPA_POLICY_DIR
        value: "/policies"
      
      # Ledger writer endpoint
      - name: SXS_LEDGER_URL
        value: "http://ledger.chainbridge.svc.cluster.local:8080"
      
      # Performance targets
      - name: POLICY_EVAL_TIMEOUT_MS
        value: "10"
    
    # IG Node security context
    securityContext:
      runAsNonRoot: true
      runAsUser: 1001  # Different UID from agent
      capabilities:
        drop:
          - ALL
        add:
          - NET_BIND_SERVICE  # Bind to port 9999 (proxy)
    
    # Volume mounts
    volumeMounts:
      - name: opa-policies
        mountPath: /policies
        readOnly: true  # Policies are read-only (updated via ConfigMap)
      - name: ig-fuse-overlay
        mountPath: /mnt/agent-overlay
      - name: ig-logs
        mountPath: /var/log/ig
    
    # Resource limits
    resources:
      limits:
        cpu: "1"
        memory: "2Gi"
      requests:
        cpu: "500m"
        memory: "1Gi"
    
    # Liveness and readiness probes
    livenessProbe:
      httpGet:
        path: /health
        port: 9999
      initialDelaySeconds: 10
      periodSeconds: 5
      timeoutSeconds: 3
      failureThreshold: 3
    
    readinessProbe:
      httpGet:
        path: /ready
        port: 9999
      initialDelaySeconds: 5
      periodSeconds: 3
      timeoutSeconds: 2
  
  # ========================================
  # VOLUMES
  # ========================================
  volumes:
    # Shared tmpfs for agent writes (ephemeral)
    - name: writable-tmp
      emptyDir:
        medium: Memory
        sizeLimit: 1Gi
    
    # FUSE overlay for IG-controlled writes
    - name: ig-fuse-overlay
      emptyDir: {}
    
    # OPA policies (from ConfigMap)
    - name: opa-policies
      configMap:
        name: ig-opa-policies
    
    # IG logs (persistent)
    - name: ig-logs
      persistentVolumeClaim:
        claimName: ig-logs-pvc
  
  # ========================================
  # INIT CONTAINER: IG Preflight
  # ========================================
  initContainers:
  - name: ig-preflight
    image: chainbridge/ig-node:v1.0.0
    command: ["/bin/sh", "-c"]
    args:
      - |
        echo "IG Node Preflight Check"
        # Verify OPA policies are loaded
        if [ ! -f /policies/constitutional/invariants.rego ]; then
          echo "ERROR: OPA policies not found"
          exit 1
        fi
        # Verify DB connectivity
        nc -zv ${POSTGRES_HOST} ${POSTGRES_PORT} || exit 1
        echo "IG Node preflight PASSED"
    env:
      - name: POSTGRES_HOST
        value: "postgres.chainbridge.svc.cluster.local"
      - name: POSTGRES_PORT
        value: "5432"
    volumeMounts:
      - name: opa-policies
        mountPath: /policies
```

### 2.2 Network Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Agent Container (GID-00 to GID-10)                         │
│                                                              │
│  Agent wants to:                                            │
│  1. HTTP request to external API                           │
│  2. SQL query to database                                  │
│  3. File write to /app/writable/                           │
│                                                              │
└──────────────┬──────────────────────────────────────────────┘
               │
               │ ALL traffic proxied through IG Node
               ▼
┌──────────────────────────────────────────────────────────────┐
│  IG Node Container (GID-12)                                  │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ HTTP Proxy (port 9999)                              │    │
│  │ - Intercepts HTTP/HTTPS requests                    │    │
│  │ - Evaluates OPA policy: allow_http_request(input)   │    │
│  │ - Decision: ALLOW | BLOCK                           │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ DB Proxy (port 5433 → 5432)                         │    │
│  │ - Intercepts SQL queries (PgBouncer)                │    │
│  │ - Evaluates OPA policy: allow_sql_query(input)      │    │
│  │ - Query rewriting for audit logs                    │    │
│  │ - Decision: ALLOW | BLOCK                           │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ FUSE Overlay (filesystem interception)              │    │
│  │ - Intercepts file writes to /app/writable/          │    │
│  │ - Evaluates OPA policy: allow_file_write(input)     │    │
│  │ - Decision: ALLOW | BLOCK                           │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ OPA Policy Engine (core decision logic)             │    │
│  │ - Load policies from /policies/*.rego               │    │
│  │ - Direct DB queries (epistemic independence)        │    │
│  │ - Evaluate invariants, generate Dissent Objects     │    │
│  │ - Log to SXS Ledger (immutable audit trail)         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
└───────────────────────┬───────────────────────────────────────┘
                        │
                        │ If ALLOW → Forward to destination
                        │ If BLOCK → Return Dissent Object
                        ▼
              ┌─────────────────────────┐
              │  Destination             │
              │  - External API          │
              │  - PostgreSQL Database   │
              │  - File System           │
              └─────────────────────────┘
```

---

## 3. Traffic Interception Mechanisms

### 3.1 HTTP Proxy Mode

**Technology:** Envoy Proxy or custom HTTP proxy (Go)

**Configuration:**

```yaml
# envoy.yaml (IG Node HTTP Proxy)
static_resources:
  listeners:
  - name: http_proxy
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 9999
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ig_http_proxy
          codec_type: AUTO
          route_config:
            name: local_route
            virtual_hosts:
            - name: backend
              domains: ["*"]
              routes:
              - match:
                  prefix: "/"
                route:
                  cluster: dynamic_forward_proxy
          http_filters:
          # IG OPA Authorization Filter
          - name: envoy.filters.http.ext_authz
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.ext_authz.v3.ExtAuthz
              grpc_service:
                envoy_grpc:
                  cluster_name: opa_service
                timeout: 0.010s  # 10ms policy evaluation
              failure_mode_allow: false  # FAIL-CLOSED
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  
  clusters:
  - name: opa_service
    connect_timeout: 0.005s
    type: STATIC
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: opa_service
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: 127.0.0.1
                port_value: 8181  # OPA gRPC port
```

**OPA Policy (Rego):**

```rego
package http.authz

import future.keywords.if
import future.keywords.in

# Default deny (fail-closed)
default allow := false

# Allow HTTP request if all policies pass
allow if {
    not violates_invariants
    not is_dangerous_endpoint
    within_rate_limits
}

# Check constitutional invariants
violates_invariants if {
    # Example: Block external API calls if SCRAM not implemented
    input.request.path == "/api/external"
    not scram_exists
}

scram_exists if {
    # Direct DB query (epistemic independence)
    query := "SELECT COUNT(*) FROM modules WHERE name = 'scram' AND status = 'deployed'"
    result := db.query(query)
    result[0].count > 0
}

# Block dangerous endpoints
is_dangerous_endpoint if {
    input.request.path == "/admin/delete_all"
}

# Rate limiting
within_rate_limits if {
    # Check request count from ledger
    agent := input.request.headers["X-Agent-GID"]
    count := ledger.request_count(agent, "1h")
    count < 1000  # Max 1000 req/hour
}

# If denied, generate Dissent Object
dissent[obj] if {
    not allow
    obj := {
        "dissent_id": generate_uuid(),
        "actor": input.request.headers["X-Agent-GID"],
        "action": input.request.method,
        "policy_violated": violated_policies,
        "ruling": "BLOCKED",
        "timestamp": time.now_ns()
    }
}
```

### 3.2 Database Proxy Mode

**Technology:** PgBouncer with OPA integration

**Configuration:**

```ini
; pgbouncer.ini (IG Node DB Proxy)
[databases]
chainbridge = host=postgres.chainbridge.svc.cluster.local port=5432 dbname=chainbridge

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 5433
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25

; Custom: Query interceptor (hooks into PgBouncer via plugin)
query_interceptor = /usr/local/bin/opa_sql_interceptor
```

**OPA SQL Policy (Rego):**

```rego
package sql.authz

import future.keywords.if

default allow := false

# Allow SELECT queries (read-only epistemic access for IG itself)
allow if {
    input.actor == "GID-12"  # IG Node
    input.query_type == "SELECT"
}

# Allow INSERT/UPDATE/DELETE for agents ONLY if within authority
allow if {
    input.actor != "GID-12"  # Agents
    input.query_type in ["INSERT", "UPDATE", "DELETE"]
    authorized_table(input.table)
    not dangerous_operation(input.query)
}

# Agents cannot modify constitutional tables
authorized_table(table) if {
    table in ["logs", "metrics", "agent_state"]
    table != "invariants"  # FORBIDDEN
    table != "policies"    # FORBIDDEN
}

# Block dangerous operations
dangerous_operation(query) if {
    contains(lower(query), "drop table")
}

dangerous_operation(query) if {
    contains(lower(query), "truncate")
}
```

### 3.3 File System Interception (FUSE Overlay)

**Technology:** FUSE (Filesystem in Userspace) with OPA

**Mount:**

```bash
# IG Node starts FUSE daemon
fusermount -o allow_other /mnt/agent-overlay

# Agent container sees /app/writable/ → actually /mnt/agent-overlay (IG-controlled)
```

**FUSE Handler (Pseudo-code):**

```go
package main

import (
    "github.com/hanwen/go-fuse/v2/fuse"
    "github.com/open-policy-agent/opa/rego"
)

type IGFuseFS struct {
    opaClient *rego.Rego
}

func (fs *IGFuseFS) Write(path string, data []byte, flags uint32) (written uint32, errno syscall.Errno) {
    // Evaluate OPA policy
    input := map[string]interface{}{
        "actor": getAgentGID(),
        "action": "FILE_WRITE",
        "path": path,
        "size": len(data),
    }
    
    result, err := fs.opaClient.Eval(ctx, rego.EvalInput(input))
    if err != nil || !result.Allowed() {
        // BLOCK: Generate Dissent Object
        logDissentObject(result.Reason)
        return 0, syscall.EPERM  // Permission denied
    }
    
    // ALLOW: Write to actual filesystem
    return fs.realFS.Write(path, data, flags)
}
```

**OPA File Policy (Rego):**

```rego
package file.authz

default allow := false

# Agents can write logs
allow if {
    startswith(input.path, "/app/writable/logs/")
    input.size < 10485760  # Max 10MB per file
}

# Agents CANNOT write to code directories
deny if {
    startswith(input.path, "/app/core/")
    msg := "I-SEC-001 VIOLATION: Cannot modify core code at runtime"
}
```

---

## 4. OPA Policy Engine Integration

### 4.1 OPA Deployment

**Container:** OPA runs as a **subprocess** within IG Node container (not separate sidecar)

**Startup Command:**

```bash
#!/bin/bash
# IG Node entrypoint.sh

# Start OPA in background
opa run --server \
    --addr=localhost:8181 \
    --diagnostic-addr=localhost:8282 \
    --bundle=/policies \
    --watch \
    &

OPA_PID=$!

# Start Envoy HTTP proxy
envoy -c /etc/envoy/envoy.yaml &

# Start PgBouncer DB proxy
pgbouncer /etc/pgbouncer/pgbouncer.ini &

# Start FUSE overlay
/usr/local/bin/ig-fuse /mnt/agent-overlay &

# Health check endpoint
python3 /app/health_server.py &

wait $OPA_PID
```

### 4.2 Policy Hot-Reload

**Mechanism:** OPA watches `/policies` directory for changes (Kubernetes ConfigMap)

**Update Flow:**

1. Jeffrey modifies Rego policy file locally
2. Jeffrey signs policy with Ed25519 key
3. Jeffrey commits to Git
4. CI/CD validates signature
5. CI/CD updates Kubernetes ConfigMap
6. OPA detects ConfigMap change (inotify)
7. OPA hot-reloads policy (no container restart)
8. IG Node logs policy update to SXS Ledger

**Policy Signature Verification (Rego):**

```rego
package meta.policy_validation

import future.keywords.if

# All policies must be signed by Jeffrey
valid_policy(policy_file) if {
    signature := read_file(sprintf("%s.sig", [policy_file]))
    public_key := data.constitutional.jeffrey_pubkey
    crypto.ed25519.verify(policy_file, signature, public_key)
}

# Block policy load if unsigned
deny[msg] if {
    policy := input.policy_file
    not valid_policy(policy)
    msg := "UNSIGNED POLICY REJECTED: Only Jeffrey can update IG policies"
}
```

---

## 5. Epistemic Independence Implementation

### 5.1 Direct Database Access

**IG Node has SEPARATE database credentials (not shared with agents):**

```sql
-- PostgreSQL: Create IG-only read user
CREATE USER ig_node WITH PASSWORD 'secure_ig_password';

-- Grant read access to ALL tables (epistemic independence)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ig_node;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO ig_node;

-- DENY write access (IG observes, does not mutate)
REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM ig_node;

-- Grant write access ONLY to dissent_objects table (IG writes vetoes)
GRANT INSERT ON TABLE dissent_objects TO ig_node;
```

**Enforcement:** Agents use different DB user (`chainbridge_app`) with write permissions. IG uses `ig_node` user (read-only + dissent writes).

### 5.2 Ledger Access

**IG Node writes directly to SXS Ledger:**

```python
# ig_node/ledger_writer.py
import requests
import nacl.signing

class LedgerWriter:
    def __init__(self, ledger_url, signing_key):
        self.ledger_url = ledger_url
        self.signing_key = signing_key
    
    def write_dissent(self, dissent_obj):
        # Sign dissent object
        message = json.dumps(dissent_obj, sort_keys=True).encode()
        signature = self.signing_key.sign(message)
        
        # Write to ledger
        response = requests.post(
            f"{self.ledger_url}/append",
            json={
                "entry_type": "DISSENT",
                "data": dissent_obj,
                "signature": signature.signature.hex(),
                "public_key": self.signing_key.verify_key.encode().hex()
            }
        )
        
        if response.status_code != 201:
            raise Exception("Ledger write failed")
        
        return response.json()["block_hash"]
```

---

## 6. Performance Optimization

### 6.1 Policy Evaluation Caching

**Challenge:** Evaluating OPA policy on every request may exceed 10ms target

**Solution:** Cache policy decisions for identical requests

```go
// IG Node policy cache (Redis)
func EvaluatePolicy(input PolicyInput) (Decision, error) {
    // Generate cache key
    cacheKey := sha256(input.Serialize())
    
    // Check cache
    if cached, found := redis.Get(cacheKey); found {
        return cached.Decision, nil
    }
    
    // Cache miss: Evaluate OPA
    decision, err := opaClient.Eval(input)
    if err != nil {
        return Deny, err
    }
    
    // Cache result (TTL: 60s)
    redis.Set(cacheKey, decision, 60*time.Second)
    
    return decision, nil
}
```

**Cache Invalidation:** When policies change (ConfigMap update), flush cache.

### 6.2 Partial Evaluation (OPA Optimization)

**OPA supports compiling policies ahead-of-time:**

```bash
# Compile Rego to WebAssembly (faster execution)
opa build -t wasm -e http/authz/allow /policies

# IG Node loads pre-compiled WASM
opa run --server --bundle=bundle.tar.gz
```

**Performance Gain:** ~5-10x faster evaluation (microseconds instead of milliseconds)

---

## 7. Deployment Instructions

### 7.1 Build IG Node Image

```dockerfile
# Dockerfile.ig-node
FROM debian:bullseye-slim AS builder

# Install OPA
RUN apt-get update && apt-get install -y wget
RUN wget https://openpolicyagent.org/downloads/v0.62.0/opa_linux_amd64_static -O /usr/local/bin/opa
RUN chmod +x /usr/local/bin/opa

# Install Envoy Proxy
RUN wget https://github.com/envoyproxy/envoy/releases/download/v1.29.0/envoy-linux-x86_64 -O /usr/local/bin/envoy
RUN chmod +x /usr/local/bin/envoy

# Install PgBouncer
RUN apt-get install -y pgbouncer

# Runtime stage
FROM debian:bullseye-slim

COPY --from=builder /usr/local/bin/opa /usr/local/bin/opa
COPY --from=builder /usr/local/bin/envoy /usr/local/bin/envoy
COPY --from=builder /usr/bin/pgbouncer /usr/bin/pgbouncer

# Copy IG Node application
COPY ig_node/ /app/
COPY policies/ /policies/

# Entrypoint
CMD ["/app/entrypoint.sh"]
```

### 7.2 Deploy to Kubernetes

```bash
# Build image
docker build -f Dockerfile.ig-node -t chainbridge/ig-node:v1.0.0 .

# Push to registry
docker push chainbridge/ig-node:v1.0.0

# Create ConfigMap for OPA policies
kubectl create configmap ig-opa-policies \
    --from-file=policies/ \
    --namespace=chainbridge

# Apply pod manifest
kubectl apply -f k8s/ig-agent-pod.yaml
```

---

## 8. Testing and Validation

### 8.1 Test Scenario: IG Blocks Unauthorized Action

```bash
# From agent container
curl -X POST http://localhost:9999/api/admin/delete_all

# Expected response (from IG Node):
{
  "dissent_id": "DISSENT-2026-01-25-002",
  "ruling": "BLOCKED",
  "policy_violated": "is_dangerous_endpoint",
  "reasoning": "Endpoint /admin/delete_all is prohibited",
  "signed_by": "GID-12",
  "timestamp": "2026-01-25T16:00:00Z"
}
```

### 8.2 Test Scenario: IG Allows Authorized Action

```bash
# From agent container
curl -X GET http://localhost:9999/api/metrics

# Expected response (proxied through IG, allowed):
{
  "metrics": {
    "cpu_usage": 45.2,
    "memory_usage": 2048
  }
}
```

---

## 9. Monitoring and Observability

### 9.1 Metrics Exported

**Prometheus metrics from IG Node:**

```
# Policy evaluation latency
ig_policy_eval_duration_seconds{policy="http.authz"} 0.008

# Allow/Block decisions
ig_decisions_total{decision="allow"} 1234
ig_decisions_total{decision="block"} 5

# Dissent Objects generated
ig_dissent_objects_total 5

# Cache hit rate
ig_policy_cache_hit_rate 0.95
```

### 9.2 Logging

**All IG decisions logged to structured JSON:**

```json
{
  "timestamp": "2026-01-25T16:05:00Z",
  "actor": "GID-00",
  "action": "HTTP_POST",
  "target": "/api/execute_pac",
  "decision": "BLOCK",
  "policy_violated": "I-SCRAM-001",
  "dissent_id": "DISSENT-2026-01-25-003",
  "ledger_block": "SXS-00123462"
}
```

---

## 10. Future Enhancements

### 10.1 Multi-IG Federation (Phase 3)

**Goal:** Byzantine Fault Tolerance with 3+ IG Nodes

**Consensus:** Action allowed only if 2/3 IG Nodes agree

### 10.2 Machine Learning Policy Optimization (Phase 4)

**Goal:** LLM generates Rego policies from natural language invariants

**Human-in-Loop:** All policies require Jeffrey signature

---

## Appendix: Simplex Architecture Reference

**NASA/CR-2000-210616:** "Simplex Architecture for Safety-Critical Systems"

**Key Principle:** Safety controller monitors and overrides primary controller

**ChainBridge Application:**
- Primary: BENSON + Agents (optimize functionality)
- Safety: GID-12 IG Node (enforce compliance)

---

**END SPECIFICATION**

**SIGNED:**
- **CINDY [GID-04]** Architecture Design
- **SAM [GID-06]** Security Review
- **DAN [GID-07]** Infrastructure Implementation
- **JEFFREY [GID-CONST-01]** Final Approval

**TIMESTAMP:** 2026-01-25T15:30:00Z  
**STATUS:** LOCKED
