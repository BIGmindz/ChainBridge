# Agent Registry Template Specification

```
════════════════════════════════════════════════════════════════════
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
GID-08 — ALEX (GOVERNANCE & ALIGNMENT ENGINE)
GOVERNANCE SPECIFICATION — NON-AUTHORITATIVE
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
════════════════════════════════════════════════════════════════════
```

## ⚠️ NON-AUTHORITATIVE DISCLAIMER

This document defines the **template specification** for the Agent Registry.

- This document is **NOT** the canonical registry
- This document does **NOT** authorize any registry changes
- The canonical registry is: `docs/governance/AGENT_REGISTRY.json`
- All registry mutations require explicit PAC authorization

---

## 1. Template Version

| Field | Value |
|-------|-------|
| Template Version | 1.0.0 |
| Schema Version | 3.0.0 |
| Effective Date | 2025-12-19 |
| Authorizing PAC | PAC-ALEX-AGENT-REGISTRY-TEMPLATE-LOCK-01 |

---

## 2. Canonical Agent Entry Template

Every agent entry in the registry **MUST** conform to this template:

```json
{
  "AGENT_NAME": {
    "gid": "GID-XX",
    "lane": "COLOR_NAME",
    "color": "COLOR_NAME",
    "emoji_primary": "🔵",
    "emoji_aliases": ["🔷", "💠"],
    "agent_level": "L2",
    "diversity_profile": ["Domain1", "Domain2"],
    "role": "Full role description",
    "role_short": "Brief role",
    "reserved_color": false,
    "aliases": [],
    "mutable_fields": ["emoji_aliases", "diversity_profile", "role", "role_short"],
    "immutable_fields": ["gid", "lane", "color", "emoji_primary"]
  }
}
```

---

## 3. Field Specifications

### 3.1 Immutable Fields (LOCKED)

These fields **MUST NOT** change without a `registry_version` bump and explicit PAC authorization.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `gid` | string | Global Identifier | Format: `GID-XX` (00-99). Immutable once assigned. |
| `lane` | string | Color lane assignment | Must match `color`. Immutable once assigned. |
| `color` | string | Primary color | Must be from approved color set. Immutable once assigned. |
| `emoji_primary` | string | Primary emoji(s) | Visual identity anchor. Immutable once assigned. |

### 3.2 Governance-Mutable Fields

These fields **MAY** change via PAC authorization without a `registry_version` bump.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `agent_level` | string | Seniority level | Enum: `L0`, `L1`, `L2`, `L3` |
| `diversity_profile` | array | Specialization domains | Array of strings. Min 1, Max 8. |
| `emoji_aliases` | array | Secondary emojis | Must map to same color lane. Optional. |
| `role` | string | Full role description | Max 100 characters. |
| `role_short` | string | Brief role label | Max 30 characters. |
| `aliases` | array | Agent name aliases | Legacy name mappings. |

### 3.3 Computed/Derived Fields

These fields are informational and derived from immutable fields.

| Field | Type | Description |
|-------|------|-------------|
| `reserved_color` | boolean | Whether color is reserved (TEAL only) |

---

## 4. Agent Level Definitions

| Level | Name | Description |
|-------|------|-------------|
| `L0` | Apprentice | Learning phase, supervised execution only |
| `L1` | Specialist | Single-domain execution authority |
| `L2` | Senior | Multi-domain execution, can mentor L0/L1 |
| `L3` | Principal | Cross-domain authority, architecture decisions |

### Level Transition Rules

- L0 → L1: Requires demonstrated competence in primary domain
- L1 → L2: Requires demonstrated competence in 2+ domains
- L2 → L3: Requires architectural contribution + governance approval
- **Demotion is NOT permitted** without explicit governance override

---

## 5. Versioning Rules

### 5.1 Registry Version Bumps

| Change Type | Version Bump | PAC Required |
|-------------|--------------|--------------|
| Add new agent | MAJOR or MINOR | ✅ Yes |
| Remove agent | MAJOR | ✅ Yes |
| Change immutable field | MAJOR | ✅ Yes |
| Change mutable field | NONE | ✅ Yes |
| Fix typo in role | PATCH | ⚠️ Advisory |

### 5.2 Semver Semantics

```
MAJOR.MINOR.PATCH

MAJOR: Breaking changes (agent removal, GID reassignment)
MINOR: Non-breaking additions (new agents, new fields)
PATCH: Documentation/cosmetic fixes only
```

### 5.3 Backward Compatibility

**Backward compatibility is FORBIDDEN.**

- Old registry versions are archived, not maintained
- All consumers MUST use the current registry version
- Legacy field names (e.g., `emoji` vs `emoji_primary`) handled in code, not registry

---

## 6. Visual Alias Policy

### 6.1 Permitted Aliases

Emoji aliases are permitted under these constraints:

1. **Primary Preserved**: The `emoji_primary` field MUST NOT change
2. **Lane Alignment**: All aliases MUST visually align with the agent's color lane
3. **Cosmetic Only**: Aliases have NO semantic meaning
4. **No Authority**: Using an alias does NOT change agent permissions

### 6.2 Alias Examples

| Agent | Primary | Valid Aliases | Invalid Aliases |
|-------|---------|---------------|-----------------|
| CODY (BLUE) | 🔵 | 💠, 🔷 | 🟢, 🔴 (wrong color) |
| SAM (DARK RED) | 🟥 | 🔒, 🛡️ | 🟦 (wrong color) |
| ALEX (WHITE) | ⚪ | 📜, ⚖️ | 🟣 (wrong color) |

### 6.3 Alias Prohibitions

- ❌ Aliases MUST NOT suggest different authority levels
- ❌ Aliases MUST NOT imply cross-lane capabilities
- ❌ Aliases MUST NOT include other agents' primary emojis

---

## 7. Explicit Prohibitions

### 7.1 Forbidden Actions

| Action | Status | Reason |
|--------|--------|--------|
| Adding agents without PAC-ALEX approval | ❌ FORBIDDEN | Registry integrity |
| Changing GID assignments | ❌ FORBIDDEN | Identity immutability |
| Sharing colors across lanes without governance | ❌ FORBIDDEN | Lane isolation |
| Silent defaults or inferred fields | ❌ FORBIDDEN | Explicit declaration required |
| Runtime field mutation | ❌ FORBIDDEN | Registry is static |
| Self-modification by agents | ❌ FORBIDDEN | Governance-only changes |

### 7.2 Forbidden Interpretations

This document **MUST NOT** be interpreted as:

- ❌ Authorization to modify the canonical registry
- ❌ A roadmap for future registry features
- ❌ Implicit approval for unlisted field additions
- ❌ Permission to create alternative registries
- ❌ Justification for backward-compatible changes
- ❌ A mechanism for self-promotion of agent levels

---

## 8. Registry Metadata Requirements

The canonical registry MUST include these top-level fields:

```json
{
  "registry_version": "3.0.0",
  "last_updated": "YYYY-MM-DD",
  "change_pac": "PAC-IDENTIFIER",
  "spec_version": "2.0.0",
  "canonical_date": "YYYY-MM-DD",
  "description": "GOVERNANCE-CANONICAL description",
  "governance_invariants": { ... },
  "schema_metadata": { ... },
  "agents": { ... },
  "gid_index": { ... },
  "color_lanes": { ... },
  "forbidden_aliases": [ ... ],
  "cross_references": { ... }
}
```

---

## 9. Governance Invariants

These invariants MUST be enforced by any tooling that reads the registry:

| Invariant | Description |
|-----------|-------------|
| INV-AGENT-01 | No agent may appear in more than one color lane |
| INV-AGENT-02 | No color may be claimed without registry match |
| INV-AGENT-03 | TEAL is reserved for GID-00 (BENSON) and GID-04 (CINDY) only |
| INV-AGENT-04 | GIDs are immutable once assigned |
| INV-AGENT-05 | No new agents without explicit registry update |
| INV-AGENT-06 | Lane assignments are immutable once assigned |

---

## 10. Cross-References

| Document | Path | Purpose |
|----------|------|---------|
| Canonical Registry | `docs/governance/AGENT_REGISTRY.json` | Single source of truth |
| Registry Schema | `docs/governance/AGENT_REGISTRY_SCHEMA.json` | JSON Schema validation |
| Color Gateway Spec | `docs/governance/color_gateway_spec.json` | Color lane definitions |
| Governance Index | `docs/governance/GOVERNANCE_INDEX.md` | Master document index |

---

```
════════════════════════════════════════════════════════════════════
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
END — ALEX (GID-08) — GOVERNANCE SPECIFICATION
This document is NON-AUTHORITATIVE.
Acceptance authority: Benson (GID-00) only.
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
════════════════════════════════════════════════════════════════════
```
