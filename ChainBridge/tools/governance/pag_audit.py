#!/usr/bin/env python3
"""
PAG-01 Compliance Audit Engine — Persona Activation Governance

══════════════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-01 — CODY (BACKEND ENGINEER)
PAC-CODY-P26-PAG01-AUTOMATED-AUDIT-AND-ENFORCEMENT-01
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
══════════════════════════════════════════════════════════════════════════════

AGENT_ACTIVATION_ACK:
  agent_name: CODY
  gid: GID-01
  color: BLUE
  icon: 🔵
  role: Backend Engineer
  execution_lane: BACKEND
  authority: Benson (GID-00)
  mode: EXECUTABLE

RUNTIME_ACTIVATION_ACK:
  runtime_name: pag_audit
  gid: N/A
  authority: DELEGATED
  execution_lane: VALIDATION
  mode: FAIL_CLOSED
  executes_for_agent: CODY (GID-01)

══════════════════════════════════════════════════════════════════════════════

This module audits all governance artifacts for PAG-01 compliance:
- AGENT_ACTIVATION_ACK presence
- Registry binding validation
- Block ordering enforcement
- Fail-closed CI blocking

Authority: PAC-CODY-P26-PAG01-AUTOMATED-AUDIT-AND-ENFORCEMENT-01
Mode: FAIL_CLOSED
"""

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

# Paths
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
REGISTRY_PATH = REPO_ROOT / "docs" / "governance" / "AGENT_REGISTRY.json"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "governance"


class PAG01ViolationCode(Enum):
    """PAG-01 specific violation codes."""
    PAG_001_MISSING_BLOCK = "Missing AGENT_ACTIVATION_ACK block"
    PAG_002_MISSING_RUNTIME = "Missing RUNTIME_ACTIVATION_ACK block"
    PAG_003_REGISTRY_MISMATCH = "Agent identity does not match registry"
    PAG_004_GID_MISMATCH = "GID does not match registry for agent"
    PAG_005_ORDERING_VIOLATION = "Block ordering incorrect (runtime must precede agent)"
    PAG_006_COLOR_MISMATCH = "Color does not match registry for agent"
    PAG_007_LANE_MISMATCH = "Execution lane does not match registry for agent"
    PAG_008_ROLE_MISMATCH = "Role does not match registry for agent"
    PAG_009_ICON_MISMATCH = "Icon does not match registry for agent"
    PAG_010_INCOMPLETE_BLOCK = "AGENT_ACTIVATION_ACK missing required fields"


@dataclass
class PAG01Violation:
    """Single PAG-01 violation."""
    code: PAG01ViolationCode
    message: str
    file_path: str
    agent: Optional[str] = None
    details: Optional[dict] = None


@dataclass
class PAG01AuditResult:
    """Result of PAG-01 audit for a single file."""
    file_path: str
    compliant: bool
    violations: list = field(default_factory=list)
    agent_info: Optional[dict] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class PAG01RepoAuditResult:
    """Result of PAG-01 audit across entire repository."""
    total_files: int
    compliant_files: int
    non_compliant_files: int
    violations: list = field(default_factory=list)
    results: list = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    @property
    def all_compliant(self) -> bool:
        return self.non_compliant_files == 0
    
    def to_json(self) -> str:
        """Export as JSON for CI integration."""
        return json.dumps({
            "audit_type": "PAG-01",
            "timestamp": self.timestamp,
            "summary": {
                "total_files": self.total_files,
                "compliant": self.compliant_files,
                "non_compliant": self.non_compliant_files,
                "pass": self.all_compliant
            },
            "violations": [
                {
                    "code": v.code.name,
                    "message": v.message,
                    "file": v.file_path,
                    "agent": v.agent,
                    "details": v.details
                }
                for v in self.violations
            ],
            "files": [
                {
                    "path": r.file_path,
                    "compliant": r.compliant,
                    "agent": r.agent_info,
                    "violation_count": len(r.violations)
                }
                for r in self.results
            ]
        }, indent=2)


def load_registry() -> dict:
    """Load agent registry."""
    if not REGISTRY_PATH.exists():
        return {"agents": {}}
    return json.loads(REGISTRY_PATH.read_text())


def extract_yaml_block(content: str, block_name: str) -> Optional[dict]:
    """Extract YAML block from content."""
    # Pattern 1: ```yaml block
    pattern1 = rf'{block_name}:\s*\n```yaml\n([\s\S]*?)```'
    match1 = re.search(pattern1, content, re.IGNORECASE)
    if match1:
        return parse_yaml_fields(match1.group(1))
    
    # Pattern 2: Inline YAML
    pattern2 = rf'{block_name}:\s*\n((?:[ \t]+\w+:.*\n?)+)'
    match2 = re.search(pattern2, content, re.IGNORECASE)
    if match2:
        return parse_yaml_fields(match2.group(1))
    
    # Pattern 3: Code block with name inside
    pattern3 = rf'```yaml\n{block_name}:\s*\n([\s\S]*?)```'
    match3 = re.search(pattern3, content, re.IGNORECASE)
    if match3:
        return parse_yaml_fields(match3.group(1))
    
    return None


def parse_yaml_fields(text: str) -> dict:
    """Parse simple YAML key-value pairs."""
    result = {}
    for line in text.strip().split('\n'):
        if ':' in line and not line.strip().startswith('#'):
            key, _, value = line.partition(':')
            key = key.strip().lower().replace('-', '_')
            value = value.strip().strip('"').strip("'")
            if value:
                result[key] = value
    return result


def find_block_position(content: str, block_name: str) -> int:
    """Find position of block in content. Returns -1 if not found."""
    # Multiple patterns to find block
    patterns = [
        rf'## {block_name}',
        rf'{block_name}:',
        rf'```yaml\n{block_name}:',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.start()
    
    return -1


def is_governance_artifact(content: str) -> bool:
    """Check if content is a governance artifact (PAC or WRAP)."""
    indicators = [
        'PAC-',
        'WRAP-',
        'AGENT_ACTIVATION_ACK',
        'CORRECTION_PACK',
        'ARTIFACT_TYPE:',
    ]
    return any(ind in content for ind in indicators)


def audit_pag01_single_file(file_path: Path, registry: dict) -> PAG01AuditResult:
    """Audit a single file for PAG-01 compliance."""
    violations = []
    agent_info = None
    
    try:
        content = file_path.read_text()
    except Exception as e:
        return PAG01AuditResult(
            file_path=str(file_path),
            compliant=False,
            violations=[PAG01Violation(
                code=PAG01ViolationCode.PAG_001_MISSING_BLOCK,
                message=f"Could not read file: {e}",
                file_path=str(file_path)
            )]
        )
    
    # Skip non-governance artifacts
    if not is_governance_artifact(content):
        return PAG01AuditResult(
            file_path=str(file_path),
            compliant=True,
            violations=[]
        )
    
    # Check 1: AGENT_ACTIVATION_ACK presence
    agent_block = extract_yaml_block(content, "AGENT_ACTIVATION_ACK")
    if not agent_block:
        violations.append(PAG01Violation(
            code=PAG01ViolationCode.PAG_001_MISSING_BLOCK,
            message="AGENT_ACTIVATION_ACK block not found",
            file_path=str(file_path)
        ))
    else:
        agent_info = agent_block
        
        # Check required fields
        required_fields = ['agent_name', 'gid', 'color', 'role', 'execution_lane']
        missing = [f for f in required_fields if f not in agent_block]
        if missing:
            violations.append(PAG01Violation(
                code=PAG01ViolationCode.PAG_010_INCOMPLETE_BLOCK,
                message=f"AGENT_ACTIVATION_ACK missing fields: {missing}",
                file_path=str(file_path),
                agent=agent_block.get('agent_name'),
                details={"missing_fields": missing}
            ))
        
        # Check 3: Registry binding
        agent_name = agent_block.get('agent_name', '').upper()
        if agent_name and agent_name in registry.get('agents', {}):
            reg_agent = registry['agents'][agent_name]
            
            # GID check
            declared_gid = agent_block.get('gid', '').upper()
            expected_gid = reg_agent.get('gid', '').upper()
            if declared_gid and expected_gid and declared_gid != expected_gid:
                violations.append(PAG01Violation(
                    code=PAG01ViolationCode.PAG_004_GID_MISMATCH,
                    message=f"GID mismatch: declared '{declared_gid}', registry '{expected_gid}'",
                    file_path=str(file_path),
                    agent=agent_name,
                    details={"declared": declared_gid, "expected": expected_gid}
                ))
            
            # Color check
            declared_color = agent_block.get('color', '').upper()
            expected_color = reg_agent.get('color', '').upper()
            if declared_color and expected_color and declared_color != expected_color:
                violations.append(PAG01Violation(
                    code=PAG01ViolationCode.PAG_006_COLOR_MISMATCH,
                    message=f"Color mismatch: declared '{declared_color}', registry '{expected_color}'",
                    file_path=str(file_path),
                    agent=agent_name,
                    details={"declared": declared_color, "expected": expected_color}
                ))
            
            # Execution lane check
            declared_lane = agent_block.get('execution_lane', '').upper()
            expected_lane = reg_agent.get('execution_lane', '').upper()
            if declared_lane and expected_lane and declared_lane != expected_lane:
                violations.append(PAG01Violation(
                    code=PAG01ViolationCode.PAG_007_LANE_MISMATCH,
                    message=f"Lane mismatch: declared '{declared_lane}', registry '{expected_lane}'",
                    file_path=str(file_path),
                    agent=agent_name,
                    details={"declared": declared_lane, "expected": expected_lane}
                ))
        elif agent_name:
            violations.append(PAG01Violation(
                code=PAG01ViolationCode.PAG_003_REGISTRY_MISMATCH,
                message=f"Agent '{agent_name}' not found in registry",
                file_path=str(file_path),
                agent=agent_name
            ))
    
    # Check 2: RUNTIME_ACTIVATION_ACK presence
    runtime_block = extract_yaml_block(content, "RUNTIME_ACTIVATION_ACK")
    if not runtime_block:
        violations.append(PAG01Violation(
            code=PAG01ViolationCode.PAG_002_MISSING_RUNTIME,
            message="RUNTIME_ACTIVATION_ACK block not found",
            file_path=str(file_path),
            agent=agent_info.get('agent_name') if agent_info else None
        ))
    
    # Check 5: Block ordering (runtime before agent)
    runtime_pos = find_block_position(content, "RUNTIME_ACTIVATION_ACK")
    agent_pos = find_block_position(content, "AGENT_ACTIVATION_ACK")
    
    if runtime_pos >= 0 and agent_pos >= 0 and runtime_pos > agent_pos:
        violations.append(PAG01Violation(
            code=PAG01ViolationCode.PAG_005_ORDERING_VIOLATION,
            message="RUNTIME_ACTIVATION_ACK must appear before AGENT_ACTIVATION_ACK",
            file_path=str(file_path),
            agent=agent_info.get('agent_name') if agent_info else None,
            details={"runtime_position": runtime_pos, "agent_position": agent_pos}
        ))
    
    return PAG01AuditResult(
        file_path=str(file_path),
        compliant=len(violations) == 0,
        violations=violations,
        agent_info=agent_info
    )


def audit_pag01_repository(paths: list = None) -> PAG01RepoAuditResult:
    """Audit entire repository for PAG-01 compliance."""
    registry = load_registry()
    
    # Find all governance artifacts
    if paths:
        files = [Path(p) for p in paths if Path(p).exists()]
    else:
        files = list(GOVERNANCE_DIR.rglob("*.md"))
        # Also check pacs directory specifically
        pacs_dir = GOVERNANCE_DIR / "pacs"
        if pacs_dir.exists():
            files.extend(pacs_dir.rglob("*.md"))
        # Deduplicate
        files = list(set(files))
    
    results = []
    all_violations = []
    compliant_count = 0
    non_compliant_count = 0
    
    for file_path in sorted(files):
        result = audit_pag01_single_file(file_path, registry)
        results.append(result)
        
        if result.compliant:
            compliant_count += 1
        else:
            non_compliant_count += 1
            all_violations.extend(result.violations)
    
    return PAG01RepoAuditResult(
        total_files=len(files),
        compliant_files=compliant_count,
        non_compliant_files=non_compliant_count,
        violations=all_violations,
        results=results
    )


def print_audit_report(result: PAG01RepoAuditResult, verbose: bool = False):
    """Print human-readable audit report."""
    print("=" * 70)
    print("PAG-01 COMPLIANCE AUDIT REPORT")
    print("=" * 70)
    print(f"Timestamp: {result.timestamp}")
    print(f"Total files scanned: {result.total_files}")
    print(f"Compliant: {result.compliant_files}")
    print(f"Non-compliant: {result.non_compliant_files}")
    print()
    
    if result.all_compliant:
        print("✓ ALL FILES PAG-01 COMPLIANT")
    else:
        print("✗ PAG-01 VIOLATIONS DETECTED")
        print()
        
        # Group violations by file
        by_file = {}
        for v in result.violations:
            if v.file_path not in by_file:
                by_file[v.file_path] = []
            by_file[v.file_path].append(v)
        
        for file_path, violations in sorted(by_file.items()):
            print(f"\n{file_path}:")
            for v in violations:
                print(f"  [{v.code.name}] {v.message}")
                if verbose and v.details:
                    for k, val in v.details.items():
                        print(f"    {k}: {val}")
    
    print()
    print("=" * 70)
    if result.all_compliant:
        print("✓ AUDIT PASSED — CI MAY PROCEED")
    else:
        print("✗ AUDIT FAILED — CI BLOCKED")
    print("=" * 70)


def run_audit(
    paths: list = None,
    output_json: bool = False,
    verbose: bool = False,
    fail_on_violation: bool = True
) -> int:
    """Run PAG-01 audit. Returns exit code."""
    result = audit_pag01_repository(paths)
    
    if output_json:
        print(result.to_json())
    else:
        print_audit_report(result, verbose=verbose)
    
    if fail_on_violation and not result.all_compliant:
        return 1
    return 0


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="PAG-01 Compliance Audit — Persona Activation Governance"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Specific files to audit (default: all governance artifacts)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON for CI integration"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output with details"
    )
    parser.add_argument(
        "--no-fail",
        action="store_true",
        help="Don't return non-zero exit code on violations"
    )
    
    args = parser.parse_args()
    
    sys.exit(run_audit(
        paths=args.paths if args.paths else None,
        output_json=args.json,
        verbose=args.verbose,
        fail_on_violation=not args.no_fail
    ))


if __name__ == "__main__":
    main()

# ══════════════════════════════════════════════════════════════════════════════
# END — PAC-CODY-P26-PAG01-AUTOMATED-AUDIT-AND-ENFORCEMENT-01
# ══════════════════════════════════════════════════════════════════════════════
