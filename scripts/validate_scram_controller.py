#!/usr/bin/env python3
"""Validate Python SCRAM Controller"""
import ast
import sys

# Parse the SCRAM controller
with open('core/governance/scram.py', 'r') as f:
    source = f.read()

try:
    ast.parse(source)
    print('✓ scram.py is valid Python')
except SyntaxError as e:
    print(f'FAIL: Syntax error in scram.py: {e}')
    sys.exit(1)

# Verify critical components exist
required = ['SCRAMController', 'SCRAMState', 'MAX_TERMINATION_MS']
for req in required:
    if req not in source:
        print(f'FAIL: {req} not found in scram.py')
        sys.exit(1)
    print(f'✓ {req} present')

print('✓ SCRAM Controller validation complete')
