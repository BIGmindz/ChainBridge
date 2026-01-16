#!/usr/bin/env python3
"""Validate SCRAM Policy Governance Tier"""
import json
import sys

with open('core/governance/scram_policies.json', 'r') as f:
    policy = json.load(f)

# Check LAW tier
tier = policy.get('governance', {}).get('tier')
if tier != 'LAW':
    print(f'FAIL: Governance tier must be LAW, got {tier}')
    sys.exit(1)
print(f'✓ Governance tier: {tier}')

# Check fail-closed
fail_closed = policy.get('fail_closed', {}).get('enabled')
if not fail_closed:
    print('FAIL: fail_closed must be enabled')
    sys.exit(1)
print(f'✓ Fail-closed: {fail_closed}')

# Check dual-key
dual_key = policy.get('authorization', {}).get('dual_key_required')
if not dual_key:
    print('FAIL: dual_key_required must be true')
    sys.exit(1)
print(f'✓ Dual-key required: {dual_key}')

print('✓ Policy governance validation complete')
