#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Control Plane — Deterministic Build Script
# PAC-JEFFREY-P01: SECTION 6.4 — Containerization
#
# INVARIANTS:
# - Deterministic reproducible build
# - Git SHA tagging for traceability
# - Build date recording
# - FAIL_CLOSED on build errors
#
# Usage:
#   ./scripts/build-controlplane.sh [--push] [--tag TAG]
#
# Author: DAN (GID-07) — CI/CD Lane
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail  # FAIL_CLOSED on any error

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKERFILE_PATH="${REPO_ROOT}/infra/controlplane/Dockerfile"

# Build metadata
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
GIT_SHA=$(git rev-parse HEAD)
GIT_SHA_SHORT=$(git rev-parse --short HEAD)
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Default image settings
IMAGE_NAME="${IMAGE_NAME:-chainbridge/controlplane}"
IMAGE_TAG="${IMAGE_TAG:-${GIT_SHA_SHORT}}"

# Parse arguments
PUSH=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --push)
            PUSH=true
            shift
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ═══════════════════════════════════════════════════════════════════════════════
# PRE-FLIGHT CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "🔵 DAN (GID-07) — Control Plane Build Script"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""
echo "PAC Reference:    PAC-JEFFREY-P01"
echo "Build Date:       ${BUILD_DATE}"
echo "Git SHA:          ${GIT_SHA}"
echo "Git Branch:       ${GIT_BRANCH}"
echo "Image Name:       ${IMAGE_NAME}"
echo "Image Tag:        ${IMAGE_TAG}"
echo ""

# Verify Dockerfile exists
if [[ ! -f "${DOCKERFILE_PATH}" ]]; then
    echo "❌ FAIL_CLOSED: Dockerfile not found at ${DOCKERFILE_PATH}"
    exit 1
fi

# Verify we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ FAIL_CLOSED: Not a git repository"
    exit 1
fi

# Check for uncommitted changes (warning only)
if [[ -n "$(git status --porcelain)" ]]; then
    echo "⚠️  WARNING: Uncommitted changes detected"
    echo "   Build will proceed but image may not be reproducible"
    echo ""
fi

# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS (FAIL_CLOSED)
# ═══════════════════════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "📋 Running Control Plane Tests..."
echo "═══════════════════════════════════════════════════════════════════════════════"

cd "${REPO_ROOT}"

if [[ -f ".venv/bin/activate" ]]; then
    source .venv/bin/activate
fi

if ! pytest tests/controlplane/ -q --tb=short; then
    echo "❌ FAIL_CLOSED: Tests failed — build aborted"
    exit 1
fi

echo "✅ All Control Plane tests passed"
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# BUILD IMAGE
# ═══════════════════════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "🐳 Building Docker Image..."
echo "═══════════════════════════════════════════════════════════════════════════════"

DOCKER_BUILDKIT=1 docker build \
    --file "${DOCKERFILE_PATH}" \
    --build-arg BUILD_DATE="${BUILD_DATE}" \
    --build-arg GIT_SHA="${GIT_SHA}" \
    --tag "${IMAGE_NAME}:${IMAGE_TAG}" \
    --tag "${IMAGE_NAME}:latest" \
    --label "org.chainbridge.pac=PAC-JEFFREY-P01" \
    --label "org.chainbridge.build-date=${BUILD_DATE}" \
    --label "org.chainbridge.git-sha=${GIT_SHA}" \
    --label "org.chainbridge.git-branch=${GIT_BRANCH}" \
    "${REPO_ROOT}"

echo ""
echo "✅ Image built: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "✅ Image tagged: ${IMAGE_NAME}:latest"
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# PUSH IMAGE (optional)
# ═══════════════════════════════════════════════════════════════════════════════

if [[ "${PUSH}" == "true" ]]; then
    echo "═══════════════════════════════════════════════════════════════════════════════"
    echo "📤 Pushing Image to Registry..."
    echo "═══════════════════════════════════════════════════════════════════════════════"
    
    docker push "${IMAGE_NAME}:${IMAGE_TAG}"
    docker push "${IMAGE_NAME}:latest"
    
    echo ""
    echo "✅ Image pushed: ${IMAGE_NAME}:${IMAGE_TAG}"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# BUILD SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "🎉 BUILD COMPLETE — DAN (GID-07)"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""
echo "PAC Reference:    PAC-JEFFREY-P01"
echo "Image:            ${IMAGE_NAME}:${IMAGE_TAG}"
echo "Build Date:       ${BUILD_DATE}"
echo "Git SHA:          ${GIT_SHA}"
echo "Reproducible:     $(if [[ -z "$(git status --porcelain)" ]]; then echo "YES"; else echo "NO (uncommitted changes)"; fi)"
echo ""
echo "To run locally:"
echo "  docker run -p 8000:8000 ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
echo "To use docker-compose:"
echo "  docker-compose -f infra/controlplane/docker-compose.controlplane.yml up -d"
echo ""
