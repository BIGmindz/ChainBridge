# PDO Dependency Graph Law v1.0

**Document ID:** `DOC-GOV-DEPENDENCY-GRAPH-001`  
**PAC Reference:** `PAC-BENSON-EXEC-GOVERNANCE-MULTI-AGENT-LOAD-024`  
**Agent:** GID-01 (Cody) — Governance Lead  
**Status:** ACTIVE  
**Effective Date:** 2025-12-26

---

## 1. Purpose

This document establishes the **PDO Dependency Graph Law**, which mandates that
all PDO artifacts with cross-agent dependencies MUST declare and track those
dependencies in a directed acyclic graph (DAG) structure.

Goals:
- **Ordering Enforcement**: Ensure dependent PDOs cannot be finalized before their dependencies
- **Traceability**: Enable full lineage tracking across multi-agent executions
- **Deadlock Prevention**: Detect and prevent circular dependencies
- **Authority Isolation**: Prevent hidden authority leaks through dependency chains

---

## 2. Scope

This law applies to:
- All PDO artifacts produced under multi-agent PAC execution
- Any PDO that references output from another agent
- Cross-domain data flows (governance → risk, frontend → backend, etc.)

---

## 3. Definitions

| Term | Definition |
|------|------------|
| **Dependency** | A declared relationship where PDO-B requires PDO-A to be finalized first |
| **Upstream PDO** | A PDO that must complete before dependents can finalize |
| **Downstream PDO** | A PDO that depends on one or more upstream PDOs |
| **Dependency Graph** | DAG structure tracking all PDO dependencies in a PAC execution |
| **Dependency Edge** | Directed link from upstream to downstream PDO |
| **Topological Order** | Valid ordering where all dependencies precede dependents |

---

## 4. New Invariants (INV-AUDIT-007 → INV-AUDIT-009)

### INV-AUDIT-007: Dependency Declaration Required
Every PDO with upstream dependencies MUST declare them at creation time.
```
∀ pdo ∈ PDO_SET:
  has_dependencies(pdo) → dependencies_declared(pdo) ∧ dependencies ≠ ∅
```

### INV-AUDIT-008: Acyclic Constraint
The dependency graph MUST remain acyclic at all times.
```
∀ graph ∈ DEPENDENCY_GRAPH:
  is_directed_acyclic_graph(graph) = TRUE
```

### INV-AUDIT-009: Finalization Ordering
A PDO CANNOT be finalized until all upstream dependencies are finalized.
```
∀ pdo ∈ PDO_SET:
  finalized(pdo) → ∀ dep ∈ dependencies(pdo): finalized(dep)
```

---

## 5. Dependency Graph Structure

### 5.1 Node Structure

```python
@dataclass(frozen=True)
class DependencyNode:
    pdo_id: str                    # PDO identifier
    agent_gid: str                 # Owning agent GID
    pac_id: str                    # Parent PAC
    status: NodeStatus             # PENDING | READY | FINALIZED | BLOCKED
    created_at: str                # ISO timestamp
    finalized_at: Optional[str]    # ISO timestamp when finalized
```

### 5.2 Edge Structure

```python
@dataclass(frozen=True)
class DependencyEdge:
    edge_id: str                   # Unique edge identifier
    upstream_pdo_id: str           # Source (dependency)
    downstream_pdo_id: str         # Target (dependent)
    dependency_type: str           # DATA | APPROVAL | SEQUENCE
    created_at: str                # ISO timestamp
```

### 5.3 Graph Status Values

| Status | Description |
|--------|-------------|
| **PENDING** | Node created, waiting for dependencies |
| **READY** | All dependencies satisfied, can be finalized |
| **FINALIZED** | Node complete, dependents can proceed |
| **BLOCKED** | Upstream dependency failed or rejected |

---

## 6. Operations

### 6.1 Allowed Operations

| Operation | Description | Preconditions |
|-----------|-------------|---------------|
| `add_node(pdo)` | Add PDO to graph | PDO must be valid |
| `add_dependency(up, down)` | Create edge | Both nodes exist, no cycle created |
| `finalize_node(pdo)` | Mark as finalized | All dependencies finalized |
| `query_dependencies(pdo)` | Get upstream deps | Node exists |
| `query_dependents(pdo)` | Get downstream deps | Node exists |
| `get_topological_order()` | Get valid execution order | Graph is acyclic |
| `check_ready(pdo)` | Check if can finalize | Node exists |

### 6.2 Forbidden Operations

| Operation | Reason |
|-----------|--------|
| `remove_edge()` | Violates audit trail integrity |
| `backdate_finalization()` | Violates temporal ordering |
| `force_finalize()` | Violates INV-AUDIT-009 |
| `create_cycle()` | Violates INV-AUDIT-008 |

---

## 7. Dependency Types

| Type | Description | Use Case |
|------|-------------|----------|
| **DATA** | Output data required as input | Risk engine needs audit data |
| **APPROVAL** | Approval/sign-off required | BER requires all WRAPs |
| **SEQUENCE** | Must execute in order | CI stages |

---

## 8. Cross-Agent Dependency Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MULTI-AGENT DEPENDENCY GRAPH                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐                                                         │
│   │ PDO-A (GID-01)│ ─────────┬──────────┬──────────────────────┐           │
│   │  GOVERNANCE   │          │          │                      │           │
│   └──────────────┘          ▼          ▼                      ▼           │
│                      ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│                      │ PDO-B (GID-02)│ │ PDO-C (GID-10)│ │ PDO-D (GID-07)│    │
│                      │   FRONTEND   │ │    ML/RISK   │ │    DEVOPS    │    │
│                      └──────────────┘ └──────────────┘ └──────────────┘    │
│                             │                │                │            │
│                             └────────────────┼────────────────┘            │
│                                              ▼                              │
│                                    ┌──────────────────┐                    │
│                                    │    BER (GID-00)  │                    │
│                                    │   AGGREGATION    │                    │
│                                    └──────────────────┘                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Cycle Detection Algorithm

The graph MUST run cycle detection on every edge addition:

```python
def would_create_cycle(graph, upstream_id, downstream_id) -> bool:
    """
    Check if adding edge (upstream → downstream) would create a cycle.
    Uses DFS from downstream to see if upstream is reachable.
    """
    visited = set()
    stack = [downstream_id]
    
    while stack:
        current = stack.pop()
        if current == upstream_id:
            return True  # Cycle detected
        if current in visited:
            continue
        visited.add(current)
        
        # Add all nodes that current depends on
        for dep in graph.get_dependencies(current):
            stack.append(dep.upstream_pdo_id)
    
    return False
```

---

## 10. Finalization Protocol

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      FINALIZATION PROTOCOL                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   1. Agent requests finalization for PDO-X                                 │
│   2. Graph checks all upstream dependencies                                 │
│   3. IF any upstream NOT finalized → REJECT (status: PENDING)              │
│   4. IF any upstream BLOCKED → BLOCK PDO-X                                 │
│   5. IF all upstream FINALIZED → ALLOW finalization                        │
│   6. Update PDO-X status to FINALIZED                                      │
│   7. Notify downstream dependents they may now check readiness             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Authority Leak Prevention

To prevent hidden authority leaks through dependencies:

1. **Agent Boundary Enforcement**: Dependencies across agents require explicit declaration
2. **No Transitive Authority**: Depending on PDO-A does not grant authority of GID-A
3. **Read-Only Access**: Downstream agents get read access only to upstream outputs
4. **Audit All Crossings**: Every cross-agent dependency is logged to audit trail

---

## 12. Integration with Existing Laws

### 12.1 With PDO Audit Trail (INV-AUDIT-001 → INV-AUDIT-006)
Dependency graph operations are recorded in the audit trail.

### 12.2 With WRAP Identity Mode Law
Agent identity validated before dependency creation.

### 12.3 With BER Protocol
BER can only be issued when all WRAP dependencies are satisfied.

---

## 13. Configuration

```python
DEPENDENCY_GRAPH_CONFIG = {
    "max_depth": 10,                    # Maximum dependency chain depth
    "cycle_check_enabled": True,        # Always check for cycles
    "cross_agent_audit": True,          # Log all cross-agent deps
    "allow_self_dependency": False,     # PDO cannot depend on itself
    "finalization_timeout_seconds": 300 # Max wait for upstream
}
```

---

## 14. Enforcement

Violations result in:
- **REJECTED** status for PDO attempting invalid operations
- **BLOCKED** propagation to all downstream dependents
- **BER escalation** for ordering violations
- **Audit flag** for authority boundary violations

---

## 15. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-26 | GID-01 (Cody) | Initial release |

---

## 16. Approval

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ APPROVAL BLOCK                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ Law ID:        GOV-DEPENDENCY-GRAPH-LAW-001                                │
│ Version:       1.0                                                          │
│ Status:        ACTIVE                                                       │
│ Author:        GID-01 (Cody)                                               │
│ Reviewed By:   GID-00 (Benson Execution)                                   │
│ PAC Binding:   PAC-BENSON-EXEC-GOVERNANCE-MULTI-AGENT-LOAD-024             │
│ Effective:     2025-12-26                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

**END OF DOCUMENT**
