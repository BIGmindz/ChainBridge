"""
ProofPack API Routes — PROOFPACK_SPEC_v1.md Implementation

PAC-CODY-PROOFPACK-IMPL-01: ProofPack Generation & Offline Verification

API Endpoints:
- GET /proofpack/{pdo_id} → Generate and return ProofPack
- GET /proofpack/{pdo_id}/verify → Verify existing ProofPack
- POST /proofpack/verify → Verify uploaded ProofPack

Explicit errors for:
- PDO not found
- Artifact missing
- Verification fails

Author: CODY (GID-01) - Backend
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from core.occ.proofpack import ProofPackGenerationError, ProofPackVerificationResult, generate_proofpack, verify_proofpack
from core.occ.schemas.pdo import PDOTamperDetectedError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proofpack", tags=["ProofPack - Evidence Bundles"])


# =============================================================================
# GENERATION ENDPOINTS
# =============================================================================


@router.get(
    "/{pdo_id}",
    summary="Generate ProofPack",
    description="""
Generate a ProofPack for the specified PDO.

Returns a JSON representation of the ProofPack structure with all files.
Use `format=zip` to download as a ZIP archive.

**Per PROOFPACK_SPEC_v1.md:**
- Deterministic output (same PDO → same ProofPack, excluding export timestamp)
- Includes manifest with hash binding
- Includes all referenced artifacts
- Includes lineage chain (optional)
- Can be verified offline
    """,
    responses={
        200: {
            "description": "ProofPack generated successfully",
            "content": {
                "application/json": {},
                "application/zip": {},
            },
        },
        404: {"description": "PDO not found"},
        409: {"description": "PDO tamper detected"},
        422: {"description": "Missing required artifacts"},
    },
)
async def generate_proofpack_endpoint(
    pdo_id: UUID,
    include_lineage: bool = Query(True, description="Include lineage chain"),
    fail_on_unresolved: bool = Query(False, description="Fail if artifacts cannot be resolved"),
    format: str = Query("json", description="Output format: 'json' or 'zip'"),
):
    """Generate a ProofPack for the given PDO."""
    try:
        proofpack = generate_proofpack(
            pdo_id,
            include_lineage=include_lineage,
            fail_on_unresolved=fail_on_unresolved,
        )

        if format.lower() == "zip":
            # Create ZIP archive
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                root_dir = f"proofpack-{pdo_id}"
                for path, content in proofpack["files"].items():
                    zf.writestr(f"{root_dir}/{path}", content)

            zip_buffer.seek(0)
            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename=proofpack-{pdo_id}.zip"},
            )

        return proofpack

    except ProofPackGenerationError as e:
        logger.error(f"ProofPack generation failed: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except PDOTamperDetectedError as e:
        logger.error(f"PDO tamper detected: {e}")
        raise HTTPException(
            status_code=409,
            detail={
                "error": "PDO_TAMPER_DETECTED",
                "message": str(e),
                "pdo_id": str(e.pdo_id),
            },
        )
    except Exception as e:
        logger.exception(f"ProofPack generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate ProofPack: {e}")


@router.get(
    "/{pdo_id}/manifest",
    summary="Get ProofPack Manifest Only",
    description="Generate and return only the manifest for a PDO (lightweight).",
)
async def get_manifest_endpoint(
    pdo_id: UUID,
    include_lineage: bool = Query(True, description="Include lineage in manifest"),
) -> Dict[str, Any]:
    """Get just the manifest for a PDO."""
    try:
        proofpack = generate_proofpack(
            pdo_id,
            include_lineage=include_lineage,
        )
        return proofpack["manifest"]

    except ProofPackGenerationError as e:
        logger.error(f"Manifest generation failed: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception(f"Manifest generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate manifest: {e}")


# =============================================================================
# VERIFICATION ENDPOINTS
# =============================================================================


@router.get(
    "/{pdo_id}/verify",
    response_model=ProofPackVerificationResult,
    summary="Generate and Verify ProofPack",
    description="""
Generate a ProofPack for the PDO and immediately verify it.

This is useful for checking PDO integrity without downloading.

**Verification Steps (per spec Section 6.1):**
1. Verify PDO record hash
2. Verify all artifact hashes
3. Verify manifest hash
4. Verify lineage chain
5. Verify reference consistency
    """,
)
async def generate_and_verify_endpoint(
    pdo_id: UUID,
    include_lineage: bool = Query(True, description="Include lineage in verification"),
) -> ProofPackVerificationResult:
    """Generate and verify a ProofPack."""
    try:
        proofpack = generate_proofpack(
            pdo_id,
            include_lineage=include_lineage,
        )

        result = verify_proofpack(proofpack)
        return result

    except ProofPackGenerationError as e:
        logger.error(f"ProofPack generation failed: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception(f"Verification error: {e}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {e}")


@router.post(
    "/verify",
    response_model=ProofPackVerificationResult,
    summary="Verify Uploaded ProofPack",
    description="""
Verify an uploaded ProofPack JSON.

This endpoint accepts a ProofPack structure (as generated by GET /proofpack/{pdo_id})
and performs offline verification.

**Note:** This verification can also be performed entirely offline using
the ProofPackVerifier class or the VERIFICATION.txt instructions in the ProofPack.
    """,
)
async def verify_uploaded_proofpack(
    proofpack: Dict[str, Any],
) -> ProofPackVerificationResult:
    """Verify an uploaded ProofPack."""
    try:
        result = verify_proofpack(proofpack)
        return result
    except Exception as e:
        logger.exception(f"Verification error: {e}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {e}")


@router.post(
    "/verify/zip",
    response_model=ProofPackVerificationResult,
    summary="Verify Uploaded ProofPack ZIP",
    description="Verify an uploaded ProofPack ZIP archive.",
)
async def verify_uploaded_zip(
    file: UploadFile = File(..., description="ProofPack ZIP file"),
) -> ProofPackVerificationResult:
    """Verify an uploaded ProofPack ZIP."""
    try:
        # Read ZIP contents
        contents = await file.read()
        zip_buffer = io.BytesIO(contents)

        files: Dict[str, str] = {}
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            # Find root directory
            namelist = zf.namelist()
            if not namelist:
                raise HTTPException(status_code=400, detail="Empty ZIP file")

            # Strip root directory prefix
            root_prefix = namelist[0].split("/")[0] + "/"

            for name in namelist:
                if name.endswith("/"):  # Skip directories
                    continue

                # Read file content
                content = zf.read(name).decode("utf-8")

                # Remove root directory prefix
                relative_path = name
                if name.startswith(root_prefix):
                    relative_path = name[len(root_prefix) :]

                files[relative_path] = content

        result = verify_proofpack({"files": files})
        return result

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="ZIP contains non-UTF-8 files")
    except Exception as e:
        logger.exception(f"ZIP verification error: {e}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {e}")


# =============================================================================
# INSPECTION ENDPOINTS
# =============================================================================


@router.get(
    "/{pdo_id}/files",
    summary="List ProofPack Files",
    description="List all files that would be included in a ProofPack for this PDO.",
)
async def list_proofpack_files(
    pdo_id: UUID,
    include_lineage: bool = Query(True, description="Include lineage files"),
) -> Dict[str, Any]:
    """List files in a ProofPack without full content."""
    try:
        proofpack = generate_proofpack(
            pdo_id,
            include_lineage=include_lineage,
        )

        return {
            "pdo_id": str(pdo_id),
            "exported_at": proofpack["exported_at"],
            "file_count": len(proofpack["files"]),
            "files": [
                {
                    "path": path,
                    "size_bytes": len(content.encode("utf-8")),
                }
                for path, content in proofpack["files"].items()
            ],
        }

    except ProofPackGenerationError as e:
        logger.error(f"File listing failed: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception(f"File listing error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {e}")


@router.get(
    "/{pdo_id}/file/{file_path:path}",
    summary="Get Single ProofPack File",
    description="Get the content of a single file from the ProofPack.",
)
async def get_proofpack_file(
    pdo_id: UUID,
    file_path: str,
    include_lineage: bool = Query(True, description="Include lineage files"),
) -> Dict[str, Any]:
    """Get a single file from the ProofPack."""
    try:
        proofpack = generate_proofpack(
            pdo_id,
            include_lineage=include_lineage,
        )

        content = proofpack["files"].get(file_path)
        if content is None:
            raise HTTPException(
                status_code=404,
                detail=f"File not found in ProofPack: {file_path}",
            )

        # Parse JSON files, return as-is for others
        if file_path.endswith(".json"):
            return {
                "path": file_path,
                "content": json.loads(content),
            }

        return {
            "path": file_path,
            "content": content,
        }

    except HTTPException:
        raise
    except ProofPackGenerationError as e:
        logger.error(f"File retrieval failed: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception(f"File retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get file: {e}")
