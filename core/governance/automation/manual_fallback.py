#!/usr/bin/env python3
"""
Manual Fallback CLI for Governance Pipeline

This module provides command-line tools for human operators to intervene
in automated governance pipelines. Every automation MUST have manual fallback.

CONSTRAINT ENFORCED: No automation without manual fallback (CONS-02)

Authors:
- DAN (GID-07) - CI/CD Lead
- ATLAS (GID-11) - Automation Lead

Created: 2026-01-13
Classification: LAW_TIER
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def load_pipeline_status(pipeline_id: str, governance_root: Path) -> Optional[dict]:
    """Load current pipeline status from audit log."""
    audit_path = governance_root / "automation" / "audit_logs" / f"{pipeline_id}.log"
    
    if not audit_path.exists():
        print(f"ERROR: Pipeline {pipeline_id} not found")
        return None
    
    # Parse log entries
    entries = []
    with open(audit_path, encoding="utf-8") as f:
        for line in f:
            entries.append(line.strip())
    
    return {
        "pipeline_id": pipeline_id,
        "entries": len(entries),
        "last_entry": entries[-1] if entries else None
    }


def manual_approve(pipeline_id: str, stage: str, operator_gid: str, 
                   override_code: str, governance_root: Path) -> bool:
    """
    Manually approve a pipeline stage.
    
    This is the primary manual intervention mechanism for human operators.
    """
    print(f"\n{'='*60}")
    print(f"MANUAL APPROVAL - {stage}")
    print(f"{'='*60}")
    print(f"Pipeline: {pipeline_id}")
    print(f"Operator: {operator_gid}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # Validate operator authority
    authorized = ["GID-00", "JEFFREY"]
    if operator_gid not in authorized and "JEFFREY" not in operator_gid.upper():
        print(f"\nERROR: Operator {operator_gid} not authorized for manual override")
        print(f"Authorized operators: {authorized}")
        return False
    
    # Log the approval
    audit_path = governance_root / "automation" / "audit_logs"
    audit_path.mkdir(parents=True, exist_ok=True)
    
    approval_log = {
        "type": "MANUAL_APPROVAL",
        "pipeline_id": pipeline_id,
        "stage": stage,
        "operator_gid": operator_gid,
        "override_code_prefix": override_code[:8] + "..." if override_code else "NONE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "APPROVED"
    }
    
    with open(audit_path / f"{pipeline_id}_manual.log", "a", encoding="utf-8") as f:
        f.write(json.dumps(approval_log) + "\n")
    
    print(f"\n✓ Stage '{stage}' manually approved")
    print("✓ Audit entry created")
    return True


def manual_reject(pipeline_id: str, stage: str, operator_gid: str,
                  reason: str, governance_root: Path) -> bool:
    """
    Manually reject a pipeline stage and halt execution.
    """
    print(f"\n{'='*60}")
    print(f"MANUAL REJECTION - {stage}")
    print(f"{'='*60}")
    print(f"Pipeline: {pipeline_id}")
    print(f"Operator: {operator_gid}")
    print(f"Reason: {reason}")
    
    # Log the rejection
    audit_path = governance_root / "automation" / "audit_logs"
    audit_path.mkdir(parents=True, exist_ok=True)
    
    rejection_log = {
        "type": "MANUAL_REJECTION",
        "pipeline_id": pipeline_id,
        "stage": stage,
        "operator_gid": operator_gid,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "REJECTED"
    }
    
    with open(audit_path / f"{pipeline_id}_manual.log", "a", encoding="utf-8") as f:
        f.write(json.dumps(rejection_log) + "\n")
    
    print(f"\n✗ Stage '{stage}' manually rejected")
    print("✗ Pipeline halted")
    return True


def list_pending_approvals(governance_root: Path) -> None:
    """List all pipelines awaiting human approval."""
    print(f"\n{'='*60}")
    print("PENDING APPROVALS")
    print(f"{'='*60}")
    
    audit_path = governance_root / "automation" / "audit_logs"
    
    if not audit_path.exists():
        print("No pipelines found")
        return
    
    pending = []
    for log_file in audit_path.glob("PIPE-*.log"):
        pipeline_id = log_file.stem
        with open(log_file, encoding="utf-8") as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1]
                if "AWAITING_HUMAN" in last_line or "HUMAN_ESCALATION" in last_line:
                    pending.append(pipeline_id)
    
    if pending:
        for p in pending:
            print(f"  • {p}")
    else:
        print("No pending approvals")


def main():
    parser = argparse.ArgumentParser(
        description="Manual Fallback CLI for Governance Pipeline"
    )
    parser.add_argument(
        "--governance-root",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Path to governance directory"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check pipeline status")
    status_parser.add_argument("pipeline_id", help="Pipeline ID to check")
    
    # Approve command
    approve_parser = subparsers.add_parser("approve", help="Manually approve a stage")
    approve_parser.add_argument("pipeline_id", help="Pipeline ID")
    approve_parser.add_argument("stage", help="Stage to approve")
    approve_parser.add_argument("--gid", required=True, help="Operator GID")
    approve_parser.add_argument("--override-code", required=True, help="Override code")
    
    # Reject command
    reject_parser = subparsers.add_parser("reject", help="Manually reject a stage")
    reject_parser.add_argument("pipeline_id", help="Pipeline ID")
    reject_parser.add_argument("stage", help="Stage to reject")
    reject_parser.add_argument("--gid", required=True, help="Operator GID")
    reject_parser.add_argument("--reason", required=True, help="Rejection reason")
    
    # List pending command
    subparsers.add_parser("pending", help="List pending approvals")
    
    args = parser.parse_args()
    
    if args.command == "status":
        status = load_pipeline_status(args.pipeline_id, args.governance_root)
        if status:
            print(json.dumps(status, indent=2))
    
    elif args.command == "approve":
        manual_approve(
            args.pipeline_id,
            args.stage,
            args.gid,
            args.override_code,
            args.governance_root
        )
    
    elif args.command == "reject":
        manual_reject(
            args.pipeline_id,
            args.stage,
            args.gid,
            args.reason,
            args.governance_root
        )
    
    elif args.command == "pending":
        list_pending_approvals(args.governance_root)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
