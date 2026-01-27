#!/usr/bin/env python3
"""Test HIST-01 Invariant: Tamper Detection"""
import os
import tempfile
import sys
sys.path.insert(0, '/Users/johnbozza/Documents/Projects/ChainBridge-local-repo')

from core.audit.merkle_chronicler import MerkleChronicler

print("🔬 Testing HIST-01: Merkle Root MUST change if log is tampered\n")

with tempfile.TemporaryDirectory() as tmpdir:
    log_file = os.path.join(tmpdir, 'tamper_test.jsonl')
    
    # Create original log
    with open(log_file, 'w') as f:
        f.write('{"event": "ORIGINAL_EVENT"}\n')
    
    # Anchor original
    chronicler = MerkleChronicler([log_file], anchor_output_path=None)
    original_anchors = chronicler.anchor_logs()
    original_root = original_anchors[log_file]['merkle_root']
    print(f'📌 Original root: {original_root[:32]}...')
    
    # Tamper: Change 1 byte (ORIGINAL → TAMPERED)
    with open(log_file, 'w') as f:
        f.write('{"event": "TAMPERED_EVENT"}\n')
    print('🔧 Tampered log (changed 1 word)')
    
    # Re-anchor tampered log
    chronicler2 = MerkleChronicler([log_file], anchor_output_path=None)
    tampered_anchors = chronicler2.anchor_logs()
    tampered_root = tampered_anchors[log_file]['merkle_root']
    print(f'📌 Tampered root: {tampered_root[:32]}...')
    
    # HIST-01 Verification
    print('\n' + '='*60)
    if original_root != tampered_root:
        print('✅ HIST-01 ENFORCED: Tamper detected via root hash change')
        print('   Probability of undetected tamper: ~2^-256')
    else:
        print('❌ HIST-01 VIOLATION: Merkle root unchanged after tampering!')
        sys.exit(1)
    print('='*60)
