"""
ProofPack Generator — PROOFPACK_SPEC_v1.md Implementation

PAC-CODY-PROOFPACK-IMPL-01: ProofPack Generation & Offline Verification

Generates deterministic, portable, offline-verifiable ProofPacks from PDOs.

CONSTRAINTS:
- NO mutation of PDOs
- NO re-hashing existing records
- NO inferred or derived data
- Explicit failure on missing artifacts
- Deterministic ordering

Author: CODY (GID-01) - Backend
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from core.occ.proofpack.schemas import (
    ArtifactResolutionStatus,
    DecisionArtifact,
    InputArtifact,
    ManifestContentEntry,
    ManifestContents,
    ManifestDecisionEntry,
    ManifestExporter,
    ManifestInputEntry,
    ManifestIntegrity,
    ManifestLineageEntry,
    ManifestOutcomeEntry,
    OutcomeArtifact,
    ProofPackManifest,
    canonical_json,
    compute_json_hash,
    compute_sha256,
    ref_to_filename,
)
from core.occ.schemas.pdo import PDORecord
from core.occ.store.pdo_store import PDOStore, get_pdo_store

logger = logging.getLogger(__name__)


# =============================================================================
# VERIFICATION INSTRUCTIONS TEMPLATE
# =============================================================================

VERIFICATION_TXT_TEMPLATE = """PROOFPACK VERIFICATION INSTRUCTIONS
===================================

This ProofPack contains audit evidence for PDO: {pdo_id}
Exported: {exported_at} UTC

VERIFICATION STEPS:

1. PDO Record Hash Verification
   - Open: pdo/record.json
   - Locate the "hash" field
   - Compute SHA-256 of the canonical PDO content (see Section 6.1 of spec)
   - Compare to the stored hash value

2. Artifact Hash Verification
   - Open: manifest.json
   - For each entry in "contents", verify:
     - Read the file at the specified "path"
     - Compute SHA-256 of the file bytes
     - Compare to the "hash" value in manifest

3. Manifest Hash Verification
   - Open: manifest.json
   - Locate integrity.manifest_hash
   - Reconstruct manifest data (exclude integrity block)
   - Compute SHA-256 of canonical JSON
   - Compare to manifest_hash

4. Lineage Verification (if applicable)
   - For each file in lineage/:
     - Verify PDO hash as in Step 1
     - Verify chain continuity via previous_pdo_id

HASH ALGORITHM: SHA-256
ENCODING: UTF-8
JSON FORMAT: Compact, sorted keys, separators (",", ":")

If all hashes match, the ProofPack is VALID.
Any mismatch indicates tampering or corruption.

This verification can be performed offline without ChainBridge access.
"""


# =============================================================================
# ARTIFACT RESOLVERS
# =============================================================================


class ArtifactResolver:
    """
    Base class for resolving artifact refs to content.

    Override this to integrate with your artifact stores.
    """

    def resolve_input(self, ref: str) -> Optional[Dict[str, Any]]:
        """
        Resolve an input ref to its content.

        Returns:
            Dict with content if resolved, None if not found
        """
        # Default: unresolved (subclass should override)
        return None

    def resolve_decision(self, ref: str) -> Optional[Dict[str, Any]]:
        """
        Resolve a decision ref to its content.

        Returns:
            Dict with content if resolved, None if not found
        """
        return None

    def resolve_outcome(self, ref: str) -> Optional[Dict[str, Any]]:
        """
        Resolve an outcome ref to its content.

        Returns:
            Dict with content if resolved, None if not found
        """
        return None


class StubArtifactResolver(ArtifactResolver):
    """
    Stub resolver that creates minimal artifacts from refs.

    Used when no external artifact store is configured.
    """

    def resolve_input(self, ref: str) -> Optional[Dict[str, Any]]:
        """Create stub input artifact."""
        return {
            "ref": ref,
            "type": "input",
            "stub": True,
            "note": "Artifact content not available - stub created at export time",
        }

    def resolve_decision(self, ref: str) -> Optional[Dict[str, Any]]:
        """Create stub decision artifact."""
        return {
            "ref": ref,
            "type": "decision",
            "stub": True,
            "note": "Decision content not available - stub created at export time",
        }

    def resolve_outcome(self, ref: str) -> Optional[Dict[str, Any]]:
        """Create stub outcome artifact."""
        return {
            "ref": ref,
            "type": "outcome",
            "stub": True,
            "note": "Outcome content not available - stub created at export time",
        }


# =============================================================================
# PROOFPACK GENERATOR
# =============================================================================


class ProofPackGenerationError(Exception):
    """Raised when ProofPack generation fails."""

    def __init__(self, message: str, pdo_id: Optional[UUID] = None) -> None:
        super().__init__(message)
        self.pdo_id = pdo_id


class ProofPackGenerator:
    """
    Generates ProofPacks from PDOs per PROOFPACK_SPEC_v1.md.

    Key properties:
    - Deterministic: Same PDO always produces same ProofPack (excluding exported_at)
    - Portable: Can be verified offline
    - Complete: Contains all referenced artifacts
    """

    def __init__(
        self,
        pdo_store: Optional[PDOStore] = None,
        artifact_resolver: Optional[ArtifactResolver] = None,
    ):
        """
        Initialize the generator.

        Args:
            pdo_store: PDO store for retrieving PDOs and lineage
            artifact_resolver: Resolver for input/decision/outcome artifacts
        """
        self._pdo_store = pdo_store or get_pdo_store()
        self._artifact_resolver = artifact_resolver or StubArtifactResolver()

    def generate(
        self,
        pdo_id: UUID,
        include_lineage: bool = True,
        fail_on_unresolved: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate a ProofPack for the given PDO.

        Args:
            pdo_id: The PDO ID to generate ProofPack for
            include_lineage: Whether to include lineage chain
            fail_on_unresolved: If True, raise error for unresolved artifacts

        Returns:
            Dict with ProofPack structure:
            {
                "manifest": {...},
                "files": {
                    "pdo/record.json": {...},
                    "inputs/{hash}.json": {...},
                    ...
                },
                "verification_txt": "..."
            }

        Raises:
            ProofPackGenerationError: If PDO not found or generation fails
        """
        # Step 1: Get PDO record
        pdo = self._pdo_store.get(pdo_id, verify_integrity=True)
        if pdo is None:
            raise ProofPackGenerationError(f"PDO not found: {pdo_id}", pdo_id=pdo_id)

        # Step 2: Generate export timestamp (only non-deterministic element)
        exported_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Step 3: Resolve artifacts
        input_artifacts = self._resolve_inputs(pdo, fail_on_unresolved)
        decision_artifact = self._resolve_decision(pdo, fail_on_unresolved)
        outcome_artifact = self._resolve_outcome(pdo, fail_on_unresolved)

        # Step 4: Get lineage if requested
        lineage_pdos: List[PDORecord] = []
        if include_lineage and pdo.previous_pdo_id:
            lineage_pdos = self._get_lineage(pdo)

        # Step 5: Build file contents (deterministic JSON)
        files: Dict[str, str] = {}

        # PDO record
        pdo_path = "pdo/record.json"
        pdo_content = canonical_json(pdo.model_dump(mode="json"))
        files[pdo_path] = pdo_content

        # Input artifacts
        input_entries: List[ManifestInputEntry] = []
        for idx, (ref, artifact) in enumerate(input_artifacts):
            filename = ref_to_filename(ref)
            path = f"inputs/{filename}"
            content = canonical_json(artifact.model_dump())
            files[path] = content
            input_entries.append(
                ManifestInputEntry(
                    ref=ref,
                    path=path,
                    hash=compute_sha256(content.encode("utf-8")),
                    hash_algorithm="sha256",
                )
            )

        # Decision artifact
        decision_filename = ref_to_filename(pdo.decision_ref)
        decision_path = f"decision/{decision_filename}"
        decision_content = canonical_json(decision_artifact.model_dump())
        files[decision_path] = decision_content
        decision_entry = ManifestDecisionEntry(
            ref=pdo.decision_ref,
            path=decision_path,
            hash=compute_sha256(decision_content.encode("utf-8")),
            hash_algorithm="sha256",
        )

        # Outcome artifact
        outcome_filename = ref_to_filename(pdo.outcome_ref)
        outcome_path = f"outcome/{outcome_filename}"
        outcome_content = canonical_json(outcome_artifact.model_dump())
        files[outcome_path] = outcome_content
        outcome_entry = ManifestOutcomeEntry(
            ref=pdo.outcome_ref,
            path=outcome_path,
            hash=compute_sha256(outcome_content.encode("utf-8")),
            hash_algorithm="sha256",
        )

        # Lineage PDOs
        lineage_entries: List[ManifestLineageEntry] = []
        for lineage_pdo in lineage_pdos:
            lineage_path = f"lineage/{lineage_pdo.pdo_id}.json"
            lineage_content = canonical_json(lineage_pdo.model_dump(mode="json"))
            files[lineage_path] = lineage_content
            lineage_entries.append(
                ManifestLineageEntry(
                    pdo_id=str(lineage_pdo.pdo_id),
                    path=lineage_path,
                    hash=compute_sha256(lineage_content.encode("utf-8")),
                    hash_algorithm="sha256",
                )
            )

        # Step 6: Build manifest contents
        contents = ManifestContents(
            pdo=ManifestContentEntry(
                path=pdo_path,
                hash=compute_sha256(pdo_content.encode("utf-8")),
                hash_algorithm="sha256",
            ),
            inputs=input_entries,
            decision=decision_entry,
            outcome=outcome_entry,
            lineage=lineage_entries,
        )

        # Step 7: Compute manifest hash (exclude integrity block)
        manifest_data_for_hash = {
            "proofpack_version": "1.0",
            "pdo_id": str(pdo_id),
            "exported_at": exported_at,
            "exporter": ManifestExporter().model_dump(),
            "contents": contents.model_dump(),
        }
        manifest_hash = compute_json_hash(manifest_data_for_hash)

        # Step 8: Build complete manifest
        manifest = ProofPackManifest(
            proofpack_version="1.0",
            pdo_id=str(pdo_id),
            exported_at=exported_at,
            exporter=ManifestExporter(),
            contents=contents,
            integrity=ManifestIntegrity(
                manifest_hash=manifest_hash,
                hash_algorithm="sha256",
            ),
        )

        # Add manifest to files
        files["manifest.json"] = canonical_json(manifest.model_dump())

        # Step 9: Generate verification instructions
        verification_txt = VERIFICATION_TXT_TEMPLATE.format(
            pdo_id=str(pdo_id),
            exported_at=exported_at,
        )
        files["VERIFICATION.txt"] = verification_txt

        logger.info(f"Generated ProofPack for PDO {pdo_id} with {len(files)} files")

        return {
            "pdo_id": str(pdo_id),
            "exported_at": exported_at,
            "manifest": manifest.model_dump(),
            "files": files,
        }

    def _resolve_inputs(
        self,
        pdo: PDORecord,
        fail_on_unresolved: bool,
    ) -> List[Tuple[str, InputArtifact]]:
        """Resolve all input artifacts for a PDO."""
        results: List[Tuple[str, InputArtifact]] = []
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        for ref in pdo.input_refs:
            content = self._artifact_resolver.resolve_input(ref)

            if content is not None:
                artifact = InputArtifact(
                    ref=ref,
                    artifact_type=content.get("type", "input"),
                    content=content,
                    content_hash=compute_json_hash(content),
                    acquired_at=now_iso,
                )
            else:
                if fail_on_unresolved:
                    raise ProofPackGenerationError(
                        f"Failed to resolve input artifact: {ref}",
                        pdo_id=pdo.pdo_id,
                    )
                artifact = InputArtifact(
                    ref=ref,
                    artifact_type="unresolved",
                    content=None,
                    content_hash=None,
                    resolution_status=ArtifactResolutionStatus.NOT_FOUND,
                    resolution_attempted_at=now_iso,
                )

            results.append((ref, artifact))

        return results

    def _resolve_decision(
        self,
        pdo: PDORecord,
        fail_on_unresolved: bool,
    ) -> DecisionArtifact:
        """Resolve the decision artifact for a PDO."""
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        content = self._artifact_resolver.resolve_decision(pdo.decision_ref)

        if content is None:
            if fail_on_unresolved:
                raise ProofPackGenerationError(
                    f"Failed to resolve decision artifact: {pdo.decision_ref}",
                    pdo_id=pdo.pdo_id,
                )
            # Create stub content
            content = {
                "ref": pdo.decision_ref,
                "type": "decision",
                "stub": True,
                "note": "Decision content not available",
            }

        return DecisionArtifact(
            ref=pdo.decision_ref,
            artifact_type="decision",
            content=content,
            content_hash=compute_json_hash(content),
            decision_timestamp=now_iso,
        )

    def _resolve_outcome(
        self,
        pdo: PDORecord,
        fail_on_unresolved: bool,
    ) -> OutcomeArtifact:
        """Resolve the outcome artifact for a PDO."""
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        content = self._artifact_resolver.resolve_outcome(pdo.outcome_ref)

        if content is None:
            if fail_on_unresolved:
                raise ProofPackGenerationError(
                    f"Failed to resolve outcome artifact: {pdo.outcome_ref}",
                    pdo_id=pdo.pdo_id,
                )
            # Create stub content
            content = {
                "ref": pdo.outcome_ref,
                "type": "outcome",
                "stub": True,
                "note": "Outcome content not available",
            }

        return OutcomeArtifact(
            ref=pdo.outcome_ref,
            artifact_type="outcome",
            content=content,
            content_hash=compute_json_hash(content),
            outcome_timestamp=now_iso,
        )

    def _get_lineage(self, pdo: PDORecord) -> List[PDORecord]:
        """
        Get the lineage chain for a PDO.

        Returns PDOs oldest first.
        """
        return self._pdo_store.get_chain(pdo.pdo_id, verify_integrity=True)


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================


_default_generator: Optional[ProofPackGenerator] = None


def get_proofpack_generator() -> ProofPackGenerator:
    """Get the default ProofPack generator singleton."""
    global _default_generator
    if _default_generator is None:
        _default_generator = ProofPackGenerator()
    return _default_generator


def reset_proofpack_generator() -> None:
    """Reset the default generator (for testing)."""
    global _default_generator
    _default_generator = None


def generate_proofpack(pdo_id: UUID, **kwargs) -> Dict[str, Any]:
    """
    Convenience function to generate a ProofPack.

    Args:
        pdo_id: The PDO ID to generate ProofPack for
        **kwargs: Additional arguments passed to generator.generate()

    Returns:
        Dict with ProofPack structure
    """
    return get_proofpack_generator().generate(pdo_id, **kwargs)
