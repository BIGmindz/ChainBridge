# Agent Readiness Report Template

> Replace placeholders (e.g., `<DATE>`) before sharing.

## 1. Snapshot Header

- **Date:** `<DATE>`
- **Branch / Environment:** `<BRANCH_OR_ENV>`
- **Summary Verdict:** `<READY | DEGRADED | BLOCKED>`

## 2. Summary Metrics

- **Total Agents:** `<TOTAL_AGENTS>`
- **Valid Agents:** `<VALID_COUNT>`
- **Invalid Agents:** `<INVALID_COUNT>` (list key roles if > 0)
- **CI Status:** `agent_ci.yml` last run `<PASS | FAIL>` at `<TIMESTAMP>` (link)
- **Notable Incidents (Last 7 Days):**
  - `<INCIDENT_1>`
  - `<INCIDENT_2>`
  - `<INCIDENT_3>`

## 3. Highlights (What’s Working)

- `<HIGHLIGHT_1>`
- `<HIGHLIGHT_2>`
- `<HIGHLIGHT_3>`
- `<OPTIONAL_HIGHLIGHT_4>`
- `<OPTIONAL_HIGHLIGHT_5>`

## 4. Risks & Issues

- `<RISK_1>`
- `<RISK_2>`
- `<RISK_3>`
- `<OPTIONAL_RISK_4>`
- `<OPTIONAL_RISK_5>`

## 5. Next 30 Days – Action Plan

| Priority | Task | Owner | Target Date |
| --- | --- | --- | --- |
| P1 | `<TASK_1>` | `<OWNER_1>` | `<DATE_1>` |
| P1 | `<TASK_2>` | `<OWNER_2>` | `<DATE_2>` |
| P2 | `<TASK_3>` | `<OWNER_3>` | `<DATE_3>` |
| P3 | `<TASK_4>` | `<OWNER_4>` | `<DATE_4>` |

## 6. Reproduction / Verification Commands

```sh
python -m tools.agent_runtime --profile <PROFILE>
python -m tools.agent_validate --agents <AGENT_LIST>
python -m tools.agent_cli validate --branch <BRANCH>
pytest tests/agents/test_status.py -k agents
npm test -- AgentHealth
```

## 7. Notes

- `<FREE_FORM_NOTE>`
- `<FOLLOW_UPS>`
