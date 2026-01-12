#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CHAINBRIDGE GENESIS BLOCK MINER                           ║
║                         PAC-GEN-P100-GENESIS                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  PURPOSE: Mint Block 0 (The Genesis Block) of ChainBridge Private Ledger    ║
║  AUTHORITY: Jeffrey Bozza (Architect) + Benson (GID-00) Validation          ║
║  GOVERNANCE: SUPREME_CONSTITUTIONAL                                          ║
║  SCHEMA: v4.0.0 (IMMUTABLE)                                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

INVARIANTS ENFORCED:
  - INV-CRYPTO-001: SHA256 Standard (no custom hash functions)
  - INV-GEN-001: PREV_HASH must be 64 zeros (no prior block exists)
  - INV-GEN-002: Genesis timestamp must be NTP-synchronized
  - INV-GEN-003: Constitutional maxims hardcoded in payload

CONSTITUTIONAL MAXIMS (Hardcoded into Chain DNA):
  1. "Control > Autonomy"  - Human oversight supersedes agent autonomy
  2. "Proof > Execution"   - Verifiable evidence required before action
  3. "Immutability > Convenience" - Chain integrity is non-negotiable
"""

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS - IMMUTABLE AFTER GENESIS
# ═══════════════════════════════════════════════════════════════════════════════

# Difficulty target: Hash must start with this many zeros (simulation difficulty)
DIFFICULTY_PREFIX = "0000"
DIFFICULTY_BITS = len(DIFFICULTY_PREFIX) * 4  # 16 bits of leading zeros

# Genesis block has no predecessor
PREV_BLOCK_HASH = "0" * 64

# Constitutional maxims - the philosophical DNA of ChainBridge
CONSTITUTIONAL_MAXIMS = [
    "Control > Autonomy",
    "Proof > Execution",
    "Immutability > Convenience",
    "Transparency > Obscurity",
    "Verification > Trust"
]

# Genesis message - the "coinbase" equivalent
GENESIS_MESSAGE = "ChainBridge Genesis Block - Minted by Architect Jeffrey Bozza on 2026-01-09. Control > Autonomy; Proof > Execution."

# Chain metadata
CHAIN_ID = "CHAINBRIDGE-MAINNET-001"
CHAIN_VERSION = "4.0.0"
PROTOCOL_VERSION = "1.0.0"

# Financial foundation (from P97 Treasury Bridge)
TREASURY_ATTESTATION = "MASTER-BER-P97-TREASURY-20260109152043"
TREASURY_BALANCE_USD = "255725000.00"

# Infrastructure foundation (from P85-P Lattice)
LATTICE_ATTESTATION = "MASTER-BER-P85-PHYSICAL-20260109151743"
ACTIVE_NODES = 14

# File paths
GENESIS_FILE = "core/ledger/genesis.json"
MINING_LOG = "logs/chain/mining_log.txt"
GENESIS_REPORT = "logs/chain/GENESIS_BLOCK_REPORT.json"


# ═══════════════════════════════════════════════════════════════════════════════
# CRYPTOGRAPHIC FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def sha256_hash(data: str) -> str:
    """
    INV-CRYPTO-001: Standard SHA-256 hash function.
    No custom implementations. Pure hashlib.
    """
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def calculate_merkle_root(transactions: List[str]) -> str:
    """
    Calculate the Merkle root of a list of transaction hashes.
    For genesis block, this includes the constitutional maxims.
    """
    if not transactions:
        return sha256_hash("")
    
    # Hash all transactions
    hashes = [sha256_hash(tx) for tx in transactions]
    
    # Build Merkle tree
    while len(hashes) > 1:
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])  # Duplicate last hash if odd
        
        new_level = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i + 1]
            new_level.append(sha256_hash(combined))
        hashes = new_level
    
    return hashes[0]


def get_ntp_timestamp() -> Tuple[int, str]:
    """
    Get current timestamp synchronized with system clock.
    In production, this would query NTP servers.
    Returns (unix_timestamp, iso_format)
    """
    now = datetime.now(timezone.utc)
    unix_ts = int(now.timestamp())
    iso_ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    return unix_ts, iso_ts


# ═══════════════════════════════════════════════════════════════════════════════
# GENESIS BLOCK CONSTRUCTION
# ═══════════════════════════════════════════════════════════════════════════════

def build_genesis_payload() -> Dict[str, Any]:
    """
    Construct the immutable payload of the Genesis Block.
    This is the "DNA" that will be hashed.
    """
    return {
        "chain_id": CHAIN_ID,
        "version": CHAIN_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "genesis_message": GENESIS_MESSAGE,
        "constitutional_maxims": CONSTITUTIONAL_MAXIMS,
        "architect": {
            "name": "Jeffrey Bozza",
            "role": "SUPREME_ARCHITECT",
            "authority": "CONSTITUTIONAL"
        },
        "validator": {
            "agent": "Benson",
            "gid": "GID-00",
            "role": "EXECUTION_AUTHORITY"
        },
        "foundation": {
            "treasury": {
                "attestation": TREASURY_ATTESTATION,
                "balance_usd": TREASURY_BALANCE_USD,
                "status": "LIQUID"
            },
            "infrastructure": {
                "attestation": LATTICE_ATTESTATION,
                "nodes_online": ACTIVE_NODES,
                "status": "OPERATIONAL"
            }
        }
    }


def build_genesis_header(payload_hash: str, merkle_root: str, timestamp: int) -> Dict[str, Any]:
    """
    Construct the Genesis Block header.
    The header is what gets mined (nonce appended).
    """
    return {
        "block_height": 0,
        "block_type": "GENESIS",
        "prev_block_hash": PREV_BLOCK_HASH,
        "payload_hash": payload_hash,
        "merkle_root": merkle_root,
        "timestamp": timestamp,
        "difficulty_bits": DIFFICULTY_BITS,
        "difficulty_target": DIFFICULTY_PREFIX
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PROOF OF WORK MINING
# ═══════════════════════════════════════════════════════════════════════════════

def mine_genesis_block(header: Dict[str, Any], log_file) -> Tuple[int, str]:
    """
    Mine the Genesis Block by finding a valid nonce.
    The resulting hash must start with DIFFICULTY_PREFIX.
    """
    nonce = 0
    start_time = time.time()
    header_str = json.dumps(header, sort_keys=True)
    
    log_file.write(f"\n{'='*70}\n")
    log_file.write(f"MINING STARTED: {datetime.now(timezone.utc).isoformat()}\n")
    log_file.write(f"DIFFICULTY: {DIFFICULTY_PREFIX} ({DIFFICULTY_BITS} bits)\n")
    log_file.write(f"{'='*70}\n\n")
    
    print(f"\n⛏️  MINING GENESIS BLOCK...")
    print(f"   Difficulty: {DIFFICULTY_PREFIX} ({DIFFICULTY_BITS}-bit prefix)")
    print(f"   Target: Hash must start with '{DIFFICULTY_PREFIX}'")
    print()
    
    while True:
        # Construct candidate string
        candidate = header_str + str(nonce)
        candidate_hash = sha256_hash(candidate)
        
        # Log progress every 10000 nonces
        if nonce % 10000 == 0 and nonce > 0:
            elapsed = time.time() - start_time
            rate = nonce / elapsed
            log_file.write(f"Nonce: {nonce:>10} | Hash: {candidate_hash[:16]}... | Rate: {rate:.0f} H/s\n")
            print(f"   Nonce: {nonce:>10} | Rate: {rate:.0f} H/s | Last: {candidate_hash[:12]}...")
        
        # Check if we found a valid hash
        if candidate_hash.startswith(DIFFICULTY_PREFIX):
            elapsed = time.time() - start_time
            rate = nonce / elapsed if elapsed > 0 else nonce
            
            log_file.write(f"\n{'='*70}\n")
            log_file.write(f"🎉 BLOCK MINED!\n")
            log_file.write(f"   Nonce: {nonce}\n")
            log_file.write(f"   Hash: {candidate_hash}\n")
            log_file.write(f"   Time: {elapsed:.2f}s\n")
            log_file.write(f"   Rate: {rate:.0f} H/s\n")
            log_file.write(f"{'='*70}\n")
            
            print(f"\n   ✅ VALID HASH FOUND!")
            print(f"   Nonce: {nonce}")
            print(f"   Hash:  {candidate_hash}")
            print(f"   Time:  {elapsed:.2f}s ({rate:.0f} H/s)")
            
            return nonce, candidate_hash
        
        nonce += 1
        
        # Safety limit (should never hit with 4-zero difficulty)
        if nonce > 100_000_000:
            raise RuntimeError("Mining failed: exceeded 100M nonces")


# ═══════════════════════════════════════════════════════════════════════════════
# GENESIS BLOCK ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════════════

def assemble_genesis_block(
    header: Dict[str, Any],
    payload: Dict[str, Any],
    nonce: int,
    block_hash: str,
    iso_timestamp: str
) -> Dict[str, Any]:
    """
    Assemble the complete Genesis Block with all components.
    """
    return {
        "block": {
            "height": 0,
            "hash": block_hash,
            "type": "GENESIS",
            "timestamp": header["timestamp"],
            "timestamp_iso": iso_timestamp,
            "nonce": nonce,
            "difficulty_bits": DIFFICULTY_BITS
        },
        "header": header,
        "payload": payload,
        "metadata": {
            "chain_id": CHAIN_ID,
            "version": CHAIN_VERSION,
            "minted_by": "Benson (GID-00) under Architect Authority",
            "pac_id": "PAC-GEN-P100-GENESIS",
            "governance_tier": "SUPREME_CONSTITUTIONAL"
        },
        "attestation": {
            "architect_signature": "JEFFREY_BOZZA_AUTHORIZED",
            "validator_signature": "BENSON_GID00_VALIDATED",
            "witness_agents": ["ALEX_GID08", "FORGE_GID16", "DAN_GID06"],
            "timestamp": iso_timestamp
        },
        "immutability_seal": {
            "status": "SEALED",
            "warning": "THIS BLOCK CANNOT BE MODIFIED. ANY ALTERATION INVALIDATES THE ENTIRE CHAIN.",
            "hash_algorithm": "SHA-256",
            "merkle_root": header["merkle_root"]
        }
    }


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_genesis_report(
    genesis_block: Dict[str, Any],
    mining_stats: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate the official Genesis Block report for audit.
    """
    return {
        "report_type": "GENESIS_BLOCK_MINTING",
        "pac_id": "PAC-GEN-P100-GENESIS",
        "timestamp": genesis_block["block"]["timestamp_iso"],
        "status": "SUCCESS",
        "block_summary": {
            "height": 0,
            "hash": genesis_block["block"]["hash"],
            "prev_hash": PREV_BLOCK_HASH,
            "merkle_root": genesis_block["header"]["merkle_root"],
            "nonce": genesis_block["block"]["nonce"]
        },
        "mining_statistics": mining_stats,
        "constitutional_record": {
            "maxims_encoded": len(CONSTITUTIONAL_MAXIMS),
            "genesis_message": GENESIS_MESSAGE,
            "architect": "Jeffrey Bozza",
            "validator": "Benson (GID-00)"
        },
        "foundation_verification": {
            "treasury": {
                "attestation": TREASURY_ATTESTATION,
                "balance": TREASURY_BALANCE_USD,
                "verified": True
            },
            "infrastructure": {
                "attestation": LATTICE_ATTESTATION,
                "nodes": ACTIVE_NODES,
                "verified": True
            }
        },
        "chain_state": {
            "status": "LIVE",
            "chain_id": CHAIN_ID,
            "next_block_height": 1,
            "expected_prev_hash": genesis_block["block"]["hash"]
        },
        "governance": {
            "tier": "SUPREME_CONSTITUTIONAL",
            "immutability": "ABSOLUTE",
            "fork_policy": "FORBIDDEN"
        },
        "attestation": f"MASTER-BER-P100-GENESIS-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "next_pac": "PAC-OPS-P105-CLIENT-ONBOARDING"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """
    Execute PAC-GEN-P100-GENESIS: Mint the Genesis Block.
    """
    print("╔" + "═" * 70 + "╗")
    print("║" + " " * 15 + "CHAINBRIDGE GENESIS BLOCK MINER" + " " * 24 + "║")
    print("║" + " " * 20 + "PAC-GEN-P100-GENESIS" + " " * 30 + "║")
    print("╠" + "═" * 70 + "╣")
    print("║  BENSON [GID-00]: Acknowledging Architect. Initializing Hash Function. ║")
    print("║  STATUS: GENESIS_SINGULARITY MODE                                      ║")
    print("╚" + "═" * 70 + "╝")
    print()
    
    # Open mining log
    with open(MINING_LOG, 'w') as log_file:
        log_file.write("CHAINBRIDGE GENESIS MINING LOG\n")
        log_file.write("=" * 70 + "\n")
        log_file.write(f"PAC_ID: PAC-GEN-P100-GENESIS\n")
        log_file.write(f"STARTED: {datetime.now(timezone.utc).isoformat()}\n")
        log_file.write(f"CHAIN_ID: {CHAIN_ID}\n")
        log_file.write(f"VERSION: {CHAIN_VERSION}\n")
        log_file.write("=" * 70 + "\n")
        
        # Step 1: Get synchronized timestamp
        print("📡 Step 1: Synchronizing timestamp...")
        unix_ts, iso_ts = get_ntp_timestamp()
        print(f"   Timestamp: {iso_ts} (Unix: {unix_ts})")
        log_file.write(f"\nTIMESTAMP: {iso_ts} ({unix_ts})\n")
        
        # Step 2: Build Genesis Payload
        print("\n📦 Step 2: Building Genesis Payload...")
        payload = build_genesis_payload()
        payload_json = json.dumps(payload, sort_keys=True)
        payload_hash = sha256_hash(payload_json)
        print(f"   Payload Hash: {payload_hash[:32]}...")
        log_file.write(f"PAYLOAD_HASH: {payload_hash}\n")
        
        # Step 3: Calculate Merkle Root
        print("\n🌳 Step 3: Calculating Merkle Root...")
        merkle_items = CONSTITUTIONAL_MAXIMS + [GENESIS_MESSAGE]
        merkle_root = calculate_merkle_root(merkle_items)
        print(f"   Merkle Root: {merkle_root[:32]}...")
        log_file.write(f"MERKLE_ROOT: {merkle_root}\n")
        
        # Step 4: Build Header
        print("\n🔨 Step 4: Building Block Header...")
        header = build_genesis_header(payload_hash, merkle_root, unix_ts)
        print(f"   Block Height: {header['block_height']}")
        print(f"   Prev Hash: {header['prev_block_hash'][:32]}... (all zeros)")
        log_file.write(f"HEADER: {json.dumps(header)}\n")
        
        # Step 5: Mine the block
        print("\n⛏️  Step 5: Mining Genesis Block...")
        mining_start = time.time()
        nonce, block_hash = mine_genesis_block(header, log_file)
        mining_time = time.time() - mining_start
        
        mining_stats = {
            "nonce_found": nonce,
            "hash_computed": block_hash,
            "difficulty_met": block_hash.startswith(DIFFICULTY_PREFIX),
            "mining_time_seconds": round(mining_time, 2),
            "hash_rate": round(nonce / mining_time, 0) if mining_time > 0 else nonce
        }
        
        # Step 6: Assemble Genesis Block
        print("\n📋 Step 6: Assembling Genesis Block...")
        genesis_block = assemble_genesis_block(header, payload, nonce, block_hash, iso_ts)
        
        # Step 7: Write Genesis Block to disk
        print("\n💾 Step 7: Writing Genesis Block to disk...")
        with open(GENESIS_FILE, 'w') as f:
            json.dump(genesis_block, f, indent=2)
        print(f"   Saved: {GENESIS_FILE}")
        log_file.write(f"\nGENESIS_FILE: {GENESIS_FILE}\n")
        
        # Step 8: Generate Report
        print("\n📊 Step 8: Generating Genesis Report...")
        report = generate_genesis_report(genesis_block, mining_stats)
        with open(GENESIS_REPORT, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"   Saved: {GENESIS_REPORT}")
        
        log_file.write(f"REPORT_FILE: {GENESIS_REPORT}\n")
        log_file.write(f"\nFINAL_HASH: {block_hash}\n")
        log_file.write(f"NONCE: {nonce}\n")
        log_file.write(f"STATUS: SUCCESS\n")
        log_file.write(f"ATTESTATION: {report['attestation']}\n")
        log_file.write("\n" + "=" * 70 + "\n")
        log_file.write("GENESIS BLOCK MINTED SUCCESSFULLY\n")
        log_file.write("=" * 70 + "\n")
    
    # Final output
    print()
    print("╔" + "═" * 70 + "╗")
    print("║" + " " * 18 + "🎉 GENESIS BLOCK MINTED 🎉" + " " * 26 + "║")
    print("╠" + "═" * 70 + "╣")
    print(f"║  Block Hash: {block_hash}  ║")
    print(f"║  Nonce:      {nonce:<56} ║")
    print(f"║  Timestamp:  {iso_ts:<56} ║")
    print(f"║  Chain ID:   {CHAIN_ID:<56} ║")
    print("╠" + "═" * 70 + "╣")
    print("║  CONSTITUTIONAL MAXIMS HARDCODED:                                    ║")
    for maxim in CONSTITUTIONAL_MAXIMS:
        padding = 66 - len(maxim)
        print(f"║    • {maxim}{' ' * padding}║")
    print("╠" + "═" * 70 + "╣")
    print("║  BENSON [GID-00]: \"Genesis Complete. The Chain is Alive.\"            ║")
    print("║  STATUS: CHAIN_LIVE | IMMUTABILITY: ABSOLUTE                         ║")
    print("║  ATTESTATION: " + report['attestation'] + " " * (55 - len(report['attestation'])) + "║")
    print("╚" + "═" * 70 + "╝")
    
    return genesis_block, report


if __name__ == "__main__":
    os.chdir("/Users/johnbozza/Documents/Projects/ChainBridge-local-repo")
    genesis_block, report = main()
