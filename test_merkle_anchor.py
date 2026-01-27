#!/usr/bin/env python3
"""
Test Merkle Chronicler - Anchor sample JSONL logs
"""
from core.audit.merkle_chronicler import MerkleChronicler
import json

# Create sample audit events
sample_events = [
    {'event': 'LEGION_SPAWN', 'gid': 'GID-06', 'count': 100, 'timestamp': '2026-01-25T10:00:00Z'},
    {'event': 'CONSENSUS_REACHED', 'hash': 'abc123', 'votes': '3/5', 'timestamp': '2026-01-25T10:01:00Z'},
    {'event': 'CONTEXT_SYNC', 'agent': 'ATOM-001', 'status': 'SUCCESS', 'timestamp': '2026-01-25T10:02:00Z'}
]

# Write sample events to logs
for i, event in enumerate(sample_events):
    log_files = ['logs/legion_audit.jsonl', 'logs/hive_consensus.jsonl', 'logs/context_sync.jsonl']
    with open(log_files[i], 'a') as f:
        f.write(json.dumps(event) + '\n')

# Anchor logs
chronicler = MerkleChronicler([
    'logs/legion_audit.jsonl',
    'logs/hive_consensus.jsonl',
    'logs/context_sync.jsonl'
])
anchors = chronicler.anchor_logs()

print('\n🔒 MERKLE ANCHORING COMPLETE:')
for path, anchor in anchors.items():
    if anchor['status'] == 'ANCHORED':
        print(f'  ✅ {path}')
        print(f'     Root: {anchor["merkle_root"][:32]}...')
        print(f'     Lines: {anchor["line_count"]}')

print(f'\n📝 Anchors saved to: {chronicler.anchor_output_path}')
