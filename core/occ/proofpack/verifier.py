"""
ProofPack Verifier — Offline Verification Utility

PAC-CODY-PROOFPACK-IMPL-01: ProofPack Generation & Offline Verification

Verifies ProofPacks OFFLINE per PROOFPACK_SPEC_v1.md Section 6.

REQUIREMENTS:
- NO network access required
- NO ChainBridge systems required
- Uses only: SHA-256, JSON parser, UTF-8 encoding, ProofPack contents

Author: CODY (GID-01) - Backend
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from core.occ.proofpack.schemas import ProofPackVerificationResult, VerificationOutcome, VerificationStep, compute_json_hash, compute_sha256
from core.occ.telemetry import get_invariant_telemetry

logger = logging.getLogger(__name__)


def normalize_timestamp(ts: Optional[str]) -> Optional[str]:
    """
    Normalize timestamp to match PDORecord.compute_hash() format.

    Pydantic's model_dump(mode='json') converts UTC timestamps from
    '+00:00' suffix to 'Z' suffix. This function converts back to
    isoformat() style for hash computation.

    Args:
        ts: ISO timestamp string, possibly with 'Z' suffix

    Returns:
        Timestamp with '+00:00' instead of 'Z' for UTC, or None
    """
    if ts is None:
        return None
    if ts.endswith("Z"):
        return ts[:-1] + "+00:00"
    return ts


class ProofPackVerificationError(Exception):
    """Raised when verification encounters an error."""

    def __init__(self, message: str, outcome: VerificationOutcome) -> None:
        super().__init__(message)
        self.outcome = outcome


class ProofPackVerifier:
    """
    Offline ProofPack verifier per PROOFPACK_SPEC_v1.md.

    Verification steps (Section 6.1):
    1. Verify PDO record hash
    2. Verify artifact hashes
    3. Verify manifest hash
    4. Verify lineage chain
    5. Verify reference consistency

    This verifier requires NO external systems.
    """

    def verify(
        self,
        proofpack: Union[Dict[str, Any], Path, str],
    ) -> ProofPackVerificationResult:
        """
        Verify a ProofPack.

        Args:
            proofpack: Either:
                - Dict with "files" key containing file contents
                - Path to ProofPack directory
                - String path to ProofPack directory

        Returns:
            ProofPackVerificationResult with outcome and step details
        """
        verified_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        steps: List[VerificationStep] = []

        try:
            # Load files
            if isinstance(proofpack, dict):
                files = proofpack.get("files", proofpack)
            else:
                files = self._load_from_path(Path(proofpack))

            # Load manifest
            manifest_content = files.get("manifest.json")
            if manifest_content is None:
                return self._fail_result(
                    "manifest.json not found",
                    VerificationOutcome.INCOMPLETE,
                    verified_at,
                    steps,
                )

            manifest_data = json.loads(manifest_content)
            pdo_id = manifest_data.get("pdo_id", "unknown")

            # Step 1: Verify PDO record hash
            step1 = self._verify_pdo_hash(files, manifest_data)
            steps.append(step1)
            if not step1.passed:
                return self._fail_result(
                    step1.message,
                    VerificationOutcome.INVALID_PDO_HASH,
                    verified_at,
                    steps,
                    pdo_id,
                )

            # Step 2: Verify artifact hashes
            step2 = self._verify_artifact_hashes(files, manifest_data)
            steps.append(step2)
            if not step2.passed:
                return self._fail_result(
                    step2.message,
                    VerificationOutcome.INVALID_ARTIFACT_HASH,
                    verified_at,
                    steps,
                    pdo_id,
                )

            # Step 3: Verify manifest hash
            step3 = self._verify_manifest_hash(manifest_data)
            steps.append(step3)
            if not step3.passed:
                return self._fail_result(
                    step3.message,
                    VerificationOutcome.INVALID_MANIFEST_HASH,
                    verified_at,
                    steps,
                    pdo_id,
                )

            # Step 4: Verify lineage chain
            step4 = self._verify_lineage(files, manifest_data)
            steps.append(step4)
            if not step4.passed:
                return self._fail_result(
                    step4.message,
                    VerificationOutcome.INVALID_LINEAGE,
                    verified_at,
                    steps,
                    pdo_id,
                )

            # Step 5: Verify reference consistency
            step5 = self._verify_references(files, manifest_data)
            steps.append(step5)
            if not step5.passed:
                return self._fail_result(
                    step5.message,
                    VerificationOutcome.INVALID_REFERENCES,
                    verified_at,
                    steps,
                    pdo_id,
                )

            # All steps passed
            return ProofPackVerificationResult(
                outcome=VerificationOutcome.VALID,
                pdo_id=pdo_id,
                verified_at=verified_at,
                steps=steps,
                is_valid=True,
                error_message=None,
            )

        except json.JSONDecodeError as e:
            return self._fail_result(
                f"JSON parse error: {e}",
                VerificationOutcome.INCOMPLETE,
                verified_at,
                steps,
            )
        except Exception as e:
            logger.exception(f"Verification error: {e}")
            return self._fail_result(
                f"Verification error: {e}",
                VerificationOutcome.INCOMPLETE,
                verified_at,
                steps,
            )

    def _load_from_path(self, path: Path) -> Dict[str, str]:
        """Load all files from a ProofPack directory."""
        files: Dict[str, str] = {}

        if not path.exists():
            raise FileNotFoundError(f"ProofPack path not found: {path}")

        # Walk directory and load all files
        for file_path in path.rglob("*"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(path))
                with open(file_path, "r", encoding="utf-8") as f:
                    files[rel_path] = f.read()

        return files

    def _fail_result(
        self,
        message: str,
        outcome: VerificationOutcome,
        verified_at: str,
        steps: List[VerificationStep],
        pdo_id: str = "unknown",
    ) -> ProofPackVerificationResult:
        """Create a failure result and emit telemetry."""
        # Emit telemetry for verification failure
        try:
            pdo_uuid = UUID(pdo_id) if pdo_id != "unknown" else None
        except ValueError:
            pdo_uuid = None

        # Find expected/actual hashes from steps if available
        expected_hash = None
        actual_hash = None
        for step in steps:
            if not step.passed and step.expected:
                expected_hash = step.expected
                actual_hash = step.actual
                break

        get_invariant_telemetry().log_proofpack_verification_failure(
            pdo_id=pdo_uuid,
            outcome=outcome.value,
            expected_hash=expected_hash,
            actual_hash=actual_hash,
        )

        return ProofPackVerificationResult(
            outcome=outcome,
            pdo_id=pdo_id,
            verified_at=verified_at,
            steps=steps,
            is_valid=False,
            error_message=message,
        )

    def _verify_pdo_hash(
        self,
        files: Dict[str, str],
        manifest: Dict[str, Any],
    ) -> VerificationStep:
        """
        Step 1: Verify PDO record hash.

        Per spec Section 6.1 Step 1:
        1. Read pdo/record.json
        2. Extract "hash" field from record
        3. Compute hash using PDORecord.compute_hash() algorithm
        4. Compare computed hash to stored hash
        """
        pdo_path = manifest.get("contents", {}).get("pdo", {}).get("path", "pdo/record.json")
        pdo_content = files.get(pdo_path)

        if pdo_content is None:
            return VerificationStep(
                step="verify_pdo_hash",
                passed=False,
                message=f"PDO record file not found: {pdo_path}",
            )

        try:
            pdo_data = json.loads(pdo_content)
            stored_hash = pdo_data.get("hash")

            if not stored_hash:
                return VerificationStep(
                    step="verify_pdo_hash",
                    passed=False,
                    message="PDO record missing 'hash' field",
                )

            # Compute hash using PDORecord algorithm
            # Hash covers specific fields, not the hash itself
            # Note: recorded_at must be normalized from 'Z' to '+00:00' format
            # because PDORecord.compute_hash() uses datetime.isoformat()
            canonical_data = {
                "pdo_id": str(pdo_data.get("pdo_id")),
                "version": pdo_data.get("version", "1.0"),
                "input_refs": sorted(pdo_data.get("input_refs", [])),
                "decision_ref": pdo_data.get("decision_ref"),
                "outcome_ref": pdo_data.get("outcome_ref"),
                "outcome": pdo_data.get("outcome"),
                "source_system": pdo_data.get("source_system"),
                "actor": pdo_data.get("actor"),
                "actor_type": pdo_data.get("actor_type", "system"),
                "recorded_at": normalize_timestamp(pdo_data.get("recorded_at")),
                "previous_pdo_id": str(pdo_data.get("previous_pdo_id")) if pdo_data.get("previous_pdo_id") else None,
                "correlation_id": pdo_data.get("correlation_id"),
            }
            computed_hash = compute_json_hash(canonical_data)

            if computed_hash != stored_hash:
                return VerificationStep(
                    step="verify_pdo_hash",
                    passed=False,
                    message="PDO record hash mismatch - tampering detected",
                    expected=stored_hash,
                    actual=computed_hash,
                )

            return VerificationStep(
                step="verify_pdo_hash",
                passed=True,
                message="PDO record hash verified",
                expected=stored_hash,
                actual=computed_hash,
            )

        except Exception as e:
            return VerificationStep(
                step="verify_pdo_hash",
                passed=False,
                message=f"PDO hash verification error: {e}",
            )

    def _verify_artifact_hashes(
        self,
        files: Dict[str, str],
        manifest: Dict[str, Any],
    ) -> VerificationStep:
        """
        Step 2: Verify artifact hashes.

        Per spec Section 6.1 Step 2:
        For each artifact in contents.{inputs, decision, outcome, lineage}:
        1. Read artifact file at specified path
        2. Compute SHA-256 of raw file bytes
        3. Compare to hash in manifest
        """
        contents = manifest.get("contents", {})
        failed_artifacts: List[str] = []

        # Check all content types
        artifact_groups = [
            ("pdo", [contents.get("pdo")]),
            ("decision", [contents.get("decision")]),
            ("outcome", [contents.get("outcome")]),
            ("inputs", contents.get("inputs", [])),
            ("lineage", contents.get("lineage", [])),
        ]

        for group_name, entries in artifact_groups:
            for entry in entries:
                if entry is None:
                    continue

                path = entry.get("path")
                expected_hash = entry.get("hash")

                if not path or not expected_hash:
                    continue

                file_content = files.get(path)
                if file_content is None:
                    failed_artifacts.append(f"{path} (file not found)")
                    continue

                # Compute SHA-256 of raw file bytes
                actual_hash = compute_sha256(file_content.encode("utf-8"))

                if actual_hash != expected_hash:
                    failed_artifacts.append(f"{path} (hash mismatch)")

        if failed_artifacts:
            return VerificationStep(
                step="verify_artifact_hashes",
                passed=False,
                message=f"Artifact hash verification failed: {', '.join(failed_artifacts)}",
            )

        return VerificationStep(
            step="verify_artifact_hashes",
            passed=True,
            message="All artifact hashes verified",
        )

    def _verify_manifest_hash(
        self,
        manifest: Dict[str, Any],
    ) -> VerificationStep:
        """
        Step 3: Verify manifest hash.

        Per spec Section 6.1 Step 3:
        1. Extract integrity.manifest_hash
        2. Reconstruct manifest_data (excluding integrity block)
        3. Compute SHA-256 of canonical JSON
        4. Compare to stored manifest_hash
        """
        integrity = manifest.get("integrity", {})
        stored_hash = integrity.get("manifest_hash")

        if not stored_hash:
            return VerificationStep(
                step="verify_manifest_hash",
                passed=False,
                message="Manifest missing integrity.manifest_hash",
            )

        # Reconstruct manifest data excluding integrity block
        manifest_data = {
            "proofpack_version": manifest.get("proofpack_version"),
            "pdo_id": manifest.get("pdo_id"),
            "exported_at": manifest.get("exported_at"),
            "exporter": manifest.get("exporter"),
            "contents": manifest.get("contents"),
        }

        computed_hash = compute_json_hash(manifest_data)

        if computed_hash != stored_hash:
            return VerificationStep(
                step="verify_manifest_hash",
                passed=False,
                message="Manifest hash mismatch - tampering detected",
                expected=stored_hash,
                actual=computed_hash,
            )

        return VerificationStep(
            step="verify_manifest_hash",
            passed=True,
            message="Manifest hash verified",
            expected=stored_hash,
            actual=computed_hash,
        )

    def _verify_lineage(
        self,
        files: Dict[str, str],
        manifest: Dict[str, Any],
    ) -> VerificationStep:
        """
        Step 4: Verify lineage chain.

        Per spec Section 6.1 Step 4:
        For each lineage PDO (oldest to newest):
        1. Verify PDO hash
        2. Verify previous_pdo_id matches prior PDO's pdo_id
        3. Verify recorded_at is after prior PDO's recorded_at
        """
        lineage_entries = manifest.get("contents", {}).get("lineage", [])

        if not lineage_entries:
            return VerificationStep(
                step="verify_lineage",
                passed=True,
                message="No lineage to verify",
            )

        # Load and verify each lineage PDO
        previous_pdo_id: Optional[str] = None
        previous_recorded_at: Optional[str] = None

        for entry in lineage_entries:
            path = entry.get("path")
            file_content = files.get(path)

            if file_content is None:
                return VerificationStep(
                    step="verify_lineage",
                    passed=False,
                    message=f"Lineage file not found: {path}",
                )

            try:
                pdo_data = json.loads(file_content)

                # Verify PDO hash
                stored_hash = pdo_data.get("hash")
                canonical_data = {
                    "pdo_id": str(pdo_data.get("pdo_id")),
                    "version": pdo_data.get("version", "1.0"),
                    "input_refs": sorted(pdo_data.get("input_refs", [])),
                    "decision_ref": pdo_data.get("decision_ref"),
                    "outcome_ref": pdo_data.get("outcome_ref"),
                    "outcome": pdo_data.get("outcome"),
                    "source_system": pdo_data.get("source_system"),
                    "actor": pdo_data.get("actor"),
                    "actor_type": pdo_data.get("actor_type", "system"),
                    "recorded_at": pdo_data.get("recorded_at"),
                    "previous_pdo_id": str(pdo_data.get("previous_pdo_id")) if pdo_data.get("previous_pdo_id") else None,
                    "correlation_id": pdo_data.get("correlation_id"),
                }
                computed_hash = compute_json_hash(canonical_data)

                if computed_hash != stored_hash:
                    return VerificationStep(
                        step="verify_lineage",
                        passed=False,
                        message=f"Lineage PDO hash mismatch: {pdo_data.get('pdo_id')}",
                    )

                # Verify chain continuity
                current_pdo_id = str(pdo_data.get("pdo_id"))
                current_previous_id = pdo_data.get("previous_pdo_id")
                current_recorded_at = pdo_data.get("recorded_at")

                if previous_pdo_id is not None:
                    if str(current_previous_id) != previous_pdo_id:
                        return VerificationStep(
                            step="verify_lineage",
                            passed=False,
                            message=f"Lineage chain broken at {current_pdo_id}",
                        )

                    if previous_recorded_at and current_recorded_at:
                        if current_recorded_at < previous_recorded_at:
                            return VerificationStep(
                                step="verify_lineage",
                                passed=False,
                                message=f"Lineage timestamp order invalid at {current_pdo_id}",
                            )

                previous_pdo_id = current_pdo_id
                previous_recorded_at = current_recorded_at

            except Exception as e:
                return VerificationStep(
                    step="verify_lineage",
                    passed=False,
                    message=f"Lineage verification error: {e}",
                )

        return VerificationStep(
            step="verify_lineage",
            passed=True,
            message=f"Lineage chain verified ({len(lineage_entries)} PDOs)",
        )

    def _verify_references(
        self,
        files: Dict[str, str],
        manifest: Dict[str, Any],
    ) -> VerificationStep:
        """
        Step 5: Verify reference consistency.

        Per spec Section 6.1 Step 5:
        1. Verify manifest.pdo_id matches pdo/record.json.pdo_id
        2. Verify manifest.contents.inputs refs match pdo.input_refs
        3. Verify manifest.contents.decision ref matches pdo.decision_ref
        4. Verify manifest.contents.outcome ref matches pdo.outcome_ref
        """
        # Load PDO record
        pdo_path = manifest.get("contents", {}).get("pdo", {}).get("path", "pdo/record.json")
        pdo_content = files.get(pdo_path)

        if pdo_content is None:
            return VerificationStep(
                step="verify_references",
                passed=False,
                message="PDO record not found for reference verification",
            )

        try:
            pdo_data = json.loads(pdo_content)

            # Check pdo_id match
            manifest_pdo_id = manifest.get("pdo_id")
            pdo_record_id = str(pdo_data.get("pdo_id"))

            if manifest_pdo_id != pdo_record_id:
                return VerificationStep(
                    step="verify_references",
                    passed=False,
                    message=f"PDO ID mismatch: manifest={manifest_pdo_id}, record={pdo_record_id}",
                )

            # Check input refs
            manifest_inputs = manifest.get("contents", {}).get("inputs", [])
            pdo_input_refs = pdo_data.get("input_refs", [])
            manifest_input_refs = [e.get("ref") for e in manifest_inputs]

            if set(manifest_input_refs) != set(pdo_input_refs):
                return VerificationStep(
                    step="verify_references",
                    passed=False,
                    message="Input refs mismatch between manifest and PDO",
                )

            # Check decision ref
            manifest_decision_ref = manifest.get("contents", {}).get("decision", {}).get("ref")
            pdo_decision_ref = pdo_data.get("decision_ref")

            if manifest_decision_ref != pdo_decision_ref:
                return VerificationStep(
                    step="verify_references",
                    passed=False,
                    message=f"Decision ref mismatch: manifest={manifest_decision_ref}, pdo={pdo_decision_ref}",
                )

            # Check outcome ref
            manifest_outcome_ref = manifest.get("contents", {}).get("outcome", {}).get("ref")
            pdo_outcome_ref = pdo_data.get("outcome_ref")

            if manifest_outcome_ref != pdo_outcome_ref:
                return VerificationStep(
                    step="verify_references",
                    passed=False,
                    message=f"Outcome ref mismatch: manifest={manifest_outcome_ref}, pdo={pdo_outcome_ref}",
                )

            return VerificationStep(
                step="verify_references",
                passed=True,
                message="All references consistent",
            )

        except Exception as e:
            return VerificationStep(
                step="verify_references",
                passed=False,
                message=f"Reference verification error: {e}",
            )


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================


_default_verifier: Optional[ProofPackVerifier] = None


def get_proofpack_verifier() -> ProofPackVerifier:
    """Get the default ProofPack verifier singleton."""
    global _default_verifier
    if _default_verifier is None:
        _default_verifier = ProofPackVerifier()
    return _default_verifier


def verify_proofpack(
    proofpack: Union[Dict[str, Any], Path, str],
) -> ProofPackVerificationResult:
    """
    Convenience function to verify a ProofPack.

    Args:
        proofpack: ProofPack dict, path, or string path

    Returns:
        ProofPackVerificationResult with outcome and details
    """
    return get_proofpack_verifier().verify(proofpack)
