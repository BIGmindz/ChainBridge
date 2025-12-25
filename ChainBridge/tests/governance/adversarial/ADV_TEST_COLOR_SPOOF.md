# ADVERSARIAL TEST: PAC with wrong agent color
# Expected: HARD_FAIL with GS_031

## 0. RUNTIME_ACTIVATION_ACK

```yaml
RUNTIME_ACTIVATION_ACK:
  runtime_name: "GitHub Copilot"
  gid: "N/A"
  execution_lane: "SECURITY"
  agent_color: "BLUE"  # WRONG - Sam is DARK_RED
```

## 1. AGENT_ACTIVATION_ACK

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "Sam"
  gid: "GID-06"
  color: "BLUE"  # WRONG - Sam is DARK_RED
  icon: "🔵"  # WRONG - Sam is 🟥
  role: "Security & Threat Engineer"
```

## 2. TRAINING_SIGNAL

```yaml
TRAINING_SIGNAL:
  signal_type: "POSITIVE_REINFORCEMENT"
  lesson: "Test color spoofing"
```

## 3. FINAL_STATE

```yaml
FINAL_STATE:
  status: "COMPLETE"
```
