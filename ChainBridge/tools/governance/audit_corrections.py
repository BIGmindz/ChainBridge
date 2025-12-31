#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
ATLAS — GID-11 — CORRECTION PACK AUDIT TOOL
PAC-ATLAS-G2-GOVERNANCE-CORRECTION-HARD-GATE-IMPLEMENTATION-01
════════════════════════════════════════════════════════════════════════════════

PURPOSE:
    Scan existing correction artifacts and flag those that do not comply with
    the Gold Standard Checklist requirements. Generate forced re-correction
    PACs for non-compliant artifacts.

EXECUTING AGENT: ATLAS (GID-11)
EXECUTING COLOR: 🔵 BLUE

ENFORCEMENT:
    - Scans docs/governance/ and proofpacks/ for correction artifacts
    - Validates Gold Standard Checklist compliance
    - Reports violations with specific error codes
    - Optionally generates re-correction PACs

ERROR CODES:
    G0_020: CHECKLIST_INCOMPLETE - Gold Standard Checklist block missing or malformed
    G0_021: SELF_CERTIFICATION_MISSING - Self-certification block missing
    G0_022: VIOLATIONS_ADDRESSED_MISSING - Violations addressed section missing
    G0_023: CHECKLIST_ITEM_UNCHECKED - One or more checklist items not checked: true
    G0_024: CHECKLIST_KEY_MISSING - Required checklist key missing

════════════════════════════════════════════════════════════════════════════════
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None  # Will fall back to string-based validation


class ErrorCode(Enum):
    """Correction pack validation error codes."""
    G0_020 = "CHECKLIST_INCOMPLETE"
    G0_021 = "SELF_CERTIFICATION_MISSING"
    G0_022 = "VIOLATIONS_ADDRESSED_MISSING"
    G0_023 = "CHECKLIST_ITEM_UNCHECKED"
    G0_024 = "CHECKLIST_KEY_MISSING"


@dataclass
class ValidationError:
    """Represents a single validation error."""
    code: ErrorCode
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class AuditResult:
    """Result of auditing a single file."""
    file_path: Path
    is_correction_pack: bool
    is_compliant: bool
    errors: list[ValidationError] = field(default_factory=list)
    needs_recorrection: bool = False


@dataclass
class AuditReport:
    """Complete audit report for all scanned files."""
    timestamp: str
    total_files_scanned: int
    correction_packs_found: int
    compliant_packs: int
    non_compliant_packs: int
    results: list[AuditResult] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# GOLD STANDARD CHECKLIST KEYS
# These 13 keys are MANDATORY. ALL must be checked: true.
# ═══════════════════════════════════════════════════════════════════════════════
GOLD_STANDARD_CHECKLIST_KEYS = [
    "identity_correct",
    "agent_color_correct",
    "execution_lane_correct",
    "canonical_headers_present",
    "block_order_correct",
    "forbidden_actions_section_present",
    "scope_lock_present",
    "training_signal_present",
    "final_state_declared",
    "wrap_schema_valid",
    "no_extra_content",
    "no_scope_drift",
    "self_certification_present",
]

# ═══════════════════════════════════════════════════════════════════════════════
# CORRECTION MARKERS
# Patterns that indicate a file is a correction pack
# ═══════════════════════════════════════════════════════════════════════════════
CORRECTION_MARKERS = [
    "CORRECTION",
    "GOVERNANCE_CORRECTION",
    "MODE: GOVERNANCE_CORRECTION",
    "VIOLATIONS_ADDRESSED",
    "correction_type:",
]


def is_correction_pack(content: str) -> bool:
    """Detect if content is a correction pack based on markers."""
    return any(marker in content for marker in CORRECTION_MARKERS)


def extract_yaml_block(content: str, block_name: str) -> Optional[dict]:
    """Extract and parse a YAML block from the content."""
    if yaml is None:
        return None

    # Pattern: BLOCK_NAME:\n```yaml\n...\n```
    pattern = rf'{block_name}:\s*\n```(?:yaml)?\n(.*?)\n```'
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

    if not match:
        # Try alternative format: BLOCK_NAME:\n  key: value
        pattern2 = rf'{block_name}:\s*\n((?:[ \t]+\w+:.*\n?)+)'
        match = re.search(pattern2, content)

    if match:
        yaml_content = match.group(1)
        try:
            return yaml.safe_load(yaml_content)
        except yaml.YAMLError:
            return None

    return None


def validate_gold_standard_checklist(content: str) -> list[ValidationError]:
    """Validate the Gold Standard Checklist in a correction pack."""
    errors = []

    # Check for GOLD_STANDARD_CHECKLIST block presence
    if "GOLD_STANDARD_CHECKLIST" not in content:
        errors.append(ValidationError(
            code=ErrorCode.G0_020,
            message="GOLD_STANDARD_CHECKLIST block missing. All correction packs MUST include this block."
        ))
        return errors

    # Try to extract and parse the YAML block
    checklist = extract_yaml_block(content, "GOLD_STANDARD_CHECKLIST")

    if checklist is None:
        # Fall back to string-based validation
        return validate_gold_standard_checklist_string(content)

    # Validate each required key
    for key in GOLD_STANDARD_CHECKLIST_KEYS:
        if key not in checklist:
            errors.append(ValidationError(
                code=ErrorCode.G0_024,
                message=f"Required checklist key '{key}' is missing."
            ))
        else:
            item = checklist[key]
            # Check if the item is checked: true
            if isinstance(item, dict):
                if not item.get("checked", False):
                    errors.append(ValidationError(
                        code=ErrorCode.G0_023,
                        message=f"Checklist item '{key}' is not checked: true. Value: {item}"
                    ))
            elif isinstance(item, bool):
                if not item:
                    errors.append(ValidationError(
                        code=ErrorCode.G0_023,
                        message=f"Checklist item '{key}' is false. Must be true."
                    ))
            else:
                errors.append(ValidationError(
                    code=ErrorCode.G0_023,
                    message=f"Checklist item '{key}' has invalid format. Expected dict with 'checked: true'."
                ))

    return errors


def validate_gold_standard_checklist_string(content: str) -> list[ValidationError]:
    """Fallback string-based validation for checklist items."""
    errors = []

    for key in GOLD_STANDARD_CHECKLIST_KEYS:
        # Check if key exists in content
        if key not in content:
            errors.append(ValidationError(
                code=ErrorCode.G0_024,
                message=f"Required checklist key '{key}' is missing."
            ))
            continue

        # Check for patterns like "key: { checked: true }" or "key:\n  checked: true"
        pattern = rf'{key}:\s*(?:\{{\s*checked:\s*true\s*\}}|true|\n\s+checked:\s*true)'
        if not re.search(pattern, content, re.IGNORECASE):
            errors.append(ValidationError(
                code=ErrorCode.G0_023,
                message=f"Checklist item '{key}' is not marked as checked: true."
            ))

    return errors


def validate_self_certification(content: str) -> list[ValidationError]:
    """Validate that SELF_CERTIFICATION block is present."""
    errors = []

    if "SELF_CERTIFICATION" not in content:
        errors.append(ValidationError(
            code=ErrorCode.G0_021,
            message="SELF_CERTIFICATION block missing. All correction packs MUST include self-certification."
        ))

    return errors


def validate_violations_addressed(content: str) -> list[ValidationError]:
    """Validate that VIOLATIONS_ADDRESSED section is present."""
    errors = []

    if "VIOLATIONS_ADDRESSED" not in content:
        errors.append(ValidationError(
            code=ErrorCode.G0_022,
            message="VIOLATIONS_ADDRESSED section missing. All correction packs MUST document violations addressed."
        ))

    return errors


def audit_file(file_path: Path) -> AuditResult:
    """Audit a single file for correction pack compliance."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return AuditResult(
            file_path=file_path,
            is_correction_pack=False,
            is_compliant=False,
            errors=[ValidationError(
                code=ErrorCode.G0_020,
                message=f"Cannot read file: {e}",
                file_path=str(file_path)
            )]
        )

    # Check if this is a correction pack
    if not is_correction_pack(content):
        return AuditResult(
            file_path=file_path,
            is_correction_pack=False,
            is_compliant=True
        )

    # Validate correction pack requirements
    errors = []
    errors.extend(validate_gold_standard_checklist(content))
    errors.extend(validate_self_certification(content))
    errors.extend(validate_violations_addressed(content))

    # Set file path on all errors
    for error in errors:
        error.file_path = str(file_path)

    return AuditResult(
        file_path=file_path,
        is_correction_pack=True,
        is_compliant=len(errors) == 0,
        errors=errors,
        needs_recorrection=len(errors) > 0
    )


def find_correction_artifacts(paths: list[Path]) -> list[Path]:
    """Find all potential correction artifacts in the given paths."""
    artifacts = []

    # File patterns that might contain correction packs
    patterns = [
        "**/CORRECTION*.md",
        "**/GOVERNANCE_CORRECTION*.md",
        "**/WRAP-*CORRECTION*.md",
        "**/PAC-*CORRECTION*.md",
        "**/*correction*.md",
        "**/*correction*.py",
    ]

    for path in paths:
        if path.is_file():
            artifacts.append(path)
        elif path.is_dir():
            for pattern in patterns:
                artifacts.extend(path.glob(pattern))

    # Remove duplicates while preserving order
    seen = set()
    unique_artifacts = []
    for artifact in artifacts:
        if artifact not in seen:
            seen.add(artifact)
            unique_artifacts.append(artifact)

    return unique_artifacts


def generate_recorrection_pac(result: AuditResult) -> str:
    """Generate a forced re-correction PAC for a non-compliant artifact."""
    error_list = "\n".join([f"  - {e.code.name}: {e.message}" for e in result.errors])

    pac_content = f"""
# ════════════════════════════════════════════════════════════════════════════════
# 🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
# PAC-ATLAS-FORCED-RECORRECTION-{datetime.now().strftime('%Y%m%d%H%M%S')}
# GOVERNANCE RE-CORRECTION REQUIRED
# ════════════════════════════════════════════════════════════════════════════════

## ACTIVATION_ACK

```yaml
pac_id: PAC-ATLAS-FORCED-RECORRECTION-{datetime.now().strftime('%Y%m%d%H%M%S')}
timestamp: {datetime.now().isoformat()}Z
mode: GOVERNANCE_CORRECTION
priority: CRITICAL
```

## EXECUTING_AGENT

```yaml
agent_name: ATLAS
gid: GID-11
color: BLUE
role: Build / Repository Enforcement
```

## SCOPE

This PAC mandates the re-correction of a non-compliant correction artifact.

**Non-Compliant Artifact:** `{result.file_path}`

**Detected Violations:**
{error_list}

## OBJECTIVE

Re-apply the correction with full Gold Standard Checklist compliance.

ALL 13 checklist items MUST be `checked: true`:
- identity_correct
- agent_color_correct
- execution_lane_correct
- canonical_headers_present
- block_order_correct
- forbidden_actions_section_present
- scope_lock_present
- training_signal_present
- final_state_declared
- wrap_schema_valid
- no_extra_content
- no_scope_drift
- self_certification_present

## FORBIDDEN_ACTIONS

- Partial checklist completion
- Manual overrides or exceptions
- Skipping any checklist item
- Self-closing without full compliance

## TRAINING_SIGNAL

```yaml
signal_type: NEGATIVE
correction_type: RECORRECTION_MANDATE
target_artifact: {result.file_path}
violation_count: {len(result.errors)}
message: "Non-compliant correction artifact detected. Full re-correction required."
```

## FINAL_STATE

```yaml
state: CORRECTION_MANDATE_ISSUED
requires_action: true
blocking: true
```

# ════════════════════════════════════════════════════════════════════════════════
# END OF PAC — ATLAS (GID-11 / 🔵 BLUE)
# ════════════════════════════════════════════════════════════════════════════════
"""
    return pac_content.strip()


def run_audit(
    paths: list[Path],
    output_format: str = "text",
    generate_pacs: bool = False,
    pacs_output_dir: Optional[Path] = None
) -> AuditReport:
    """Run the full correction pack audit."""
    artifacts = find_correction_artifacts(paths)

    report = AuditReport(
        timestamp=datetime.now().isoformat(),
        total_files_scanned=len(artifacts),
        correction_packs_found=0,
        compliant_packs=0,
        non_compliant_packs=0
    )

    for artifact in artifacts:
        result = audit_file(artifact)
        report.results.append(result)

        if result.is_correction_pack:
            report.correction_packs_found += 1
            if result.is_compliant:
                report.compliant_packs += 1
            else:
                report.non_compliant_packs += 1

                if generate_pacs and pacs_output_dir:
                    pac_content = generate_recorrection_pac(result)
                    pac_filename = f"PAC-ATLAS-FORCED-RECORRECTION-{artifact.stem}.md"
                    pac_path = pacs_output_dir / pac_filename
                    pac_path.write_text(pac_content, encoding="utf-8")

    return report


def print_text_report(report: AuditReport) -> None:
    """Print the audit report in text format."""
    print("\n" + "═" * 80)
    print("🔵 ATLAS (GID-11) — CORRECTION PACK AUDIT REPORT")
    print("═" * 80)
    print(f"Timestamp: {report.timestamp}")
    print(f"Total files scanned: {report.total_files_scanned}")
    print(f"Correction packs found: {report.correction_packs_found}")
    print(f"Compliant packs: {report.compliant_packs}")
    print(f"Non-compliant packs: {report.non_compliant_packs}")
    print("═" * 80)

    if report.non_compliant_packs > 0:
        print("\n❌ NON-COMPLIANT ARTIFACTS:")
        print("-" * 80)

        for result in report.results:
            if result.is_correction_pack and not result.is_compliant:
                print(f"\n📄 {result.file_path}")
                for error in result.errors:
                    print(f"   ├── {error.code.name}: {error.message}")

        print("\n" + "=" * 80)
        print("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
        print("┃ AUDIT RESULT: VIOLATIONS DETECTED                                        ┃")
        print("┃ Re-correction required for non-compliant artifacts.                      ┃")
        print("┃ NO PARTIAL CHECKLISTS. NO MANUAL OVERRIDES. NO EXCEPTIONS.               ┃")
        print("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
    else:
        print("\n✅ ALL CORRECTION PACKS COMPLIANT")
        print("No violations detected.")

    print("\n" + "═" * 80)


def print_json_report(report: AuditReport) -> None:
    """Print the audit report in JSON format."""
    output = {
        "timestamp": report.timestamp,
        "total_files_scanned": report.total_files_scanned,
        "correction_packs_found": report.correction_packs_found,
        "compliant_packs": report.compliant_packs,
        "non_compliant_packs": report.non_compliant_packs,
        "results": [
            {
                "file_path": str(r.file_path),
                "is_correction_pack": r.is_correction_pack,
                "is_compliant": r.is_compliant,
                "errors": [
                    {
                        "code": e.code.name,
                        "message": e.message
                    }
                    for e in r.errors
                ]
            }
            for r in report.results
            if r.is_correction_pack
        ]
    }
    print(json.dumps(output, indent=2))


# ═══════════════════════════════════════════════════════════════════════════════
# G2 LEDGER CONSISTENCY VERIFICATION
# PAC-ALEX-G2-GLOBAL-AGENT-LEARNING-LEDGER-01
# ═══════════════════════════════════════════════════════════════════════════════

def verify_ledger_consistency() -> dict:
    """
    Verify ledger consistency for learning events.

    Returns a dictionary with:
    - valid: bool
    - total_entries: int
    - learning_events: int
    - issues: list of issues found
    """
    try:
        from ledger_writer import GovernanceLedger, EntryType

        ledger = GovernanceLedger()
        entries = ledger.get_all_entries()

        issues = []
        learning_events = 0

        # Track sequence continuity
        expected_seq = 1
        for entry in entries:
            seq = entry.get("sequence", 0)
            if seq != expected_seq:
                issues.append({
                    "code": "G0_051",
                    "message": f"Sequence gap: expected {expected_seq}, got {seq}",
                    "entry_id": entry.get("artifact_id")
                })
            expected_seq = seq + 1

            # Count learning events
            entry_type = entry.get("entry_type", "")
            if entry_type in [
                "CORRECTION_APPLIED",
                "BLOCK_ENFORCED",
                "LEARNING_EVENT",
                "POSITIVE_CLOSURE_ACKNOWLEDGED"
            ]:
                learning_events += 1

                # Verify authority is present for learning events
                if entry_type in ["CORRECTION_APPLIED", "BLOCK_ENFORCED", "LEARNING_EVENT"]:
                    authority = entry.get("authority_gid")
                    if not authority:
                        issues.append({
                            "code": "G0_052",
                            "message": f"Learning event missing authority_gid",
                            "entry_id": entry.get("artifact_id")
                        })

        return {
            "valid": len(issues) == 0,
            "total_entries": len(entries),
            "learning_events": learning_events,
            "issues": issues
        }

    except ImportError:
        return {
            "valid": False,
            "total_entries": 0,
            "learning_events": 0,
            "issues": [{"code": "G0_050", "message": "Ledger not available"}]
        }
    except Exception as e:
        return {
            "valid": False,
            "total_entries": 0,
            "learning_events": 0,
            "issues": [{"code": "G0_050", "message": str(e)}]
        }


def print_ledger_verification(result: dict) -> None:
    """Print ledger verification results."""
    print("\n" + "═" * 80)
    print("🩶 GLOBAL AGENT LEARNING LEDGER VERIFICATION")
    print("═" * 80)

    status = "✅ VALID" if result["valid"] else "❌ INVALID"
    print(f"\nStatus: {status}")
    print(f"Total Entries: {result['total_entries']}")
    print(f"Learning Events: {result['learning_events']}")

    if result["issues"]:
        print(f"\n⚠ Issues Found: {len(result['issues'])}")
        for issue in result["issues"]:
            print(f"  [{issue['code']}] {issue['message']}")
    else:
        print("\n✅ No issues found. Learning ledger is consistent.")

    print("\n" + "═" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="ATLAS Correction Pack Audit Tool - Scan and validate correction artifacts"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["docs/governance", "proofpacks"],
        help="Paths to scan for correction artifacts"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--generate-pacs", "-g",
        action="store_true",
        help="Generate forced re-correction PACs for non-compliant artifacts"
    )
    parser.add_argument(
        "--pacs-dir", "-d",
        type=Path,
        default=Path("proofpacks/recorrection"),
        help="Directory to output generated PACs (default: proofpacks/recorrection)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero code if violations found"
    )
    parser.add_argument(
        "--verify-ledger",
        action="store_true",
        help="Verify learning ledger consistency (G2)"
    )

    args = parser.parse_args()

    # G2: If ledger verification requested, do it first
    if args.verify_ledger:
        result = verify_ledger_consistency()
        print_ledger_verification(result)
        if args.strict and not result["valid"]:
            sys.exit(1)
        if not args.paths or args.paths == ["docs/governance", "proofpacks"]:
            # Only ledger verification requested
            sys.exit(0 if result["valid"] else 1)

    paths = [Path(p) for p in args.paths]

    # Create PACs output directory if generating PACs
    if args.generate_pacs:
        args.pacs_dir.mkdir(parents=True, exist_ok=True)

    report = run_audit(
        paths=paths,
        output_format=args.format,
        generate_pacs=args.generate_pacs,
        pacs_output_dir=args.pacs_dir if args.generate_pacs else None
    )

    if args.format == "json":
        print_json_report(report)
    else:
        print_text_report(report)

    if args.strict and report.non_compliant_packs > 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()


# ════════════════════════════════════════════════════════════════════════════════
# 🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
# END OF TOOL — ATLAS (GID-11 / 🔵 BLUE)
# PAC-ATLAS-G2-GOVERNANCE-CORRECTION-HARD-GATE-IMPLEMENTATION-01
# ════════════════════════════════════════════════════════════════════════════════
