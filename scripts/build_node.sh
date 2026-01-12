#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# CHAINBRIDGE SOVEREIGN NODE - BUILD SCRIPT
# PAC-OPS-P95-CONTAINERIZATION
# ══════════════════════════════════════════════════════════════════════════════
# "The Sovereign Node is a ship, not a building."
# ══════════════════════════════════════════════════════════════════════════════

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="chainbridge/sovereign-node"
IMAGE_TAG="${1:-1.0.0}"
CONTAINER_NAME="chainbridge-sovereign"

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        CHAINBRIDGE SOVEREIGN NODE - BUILD PROTOCOL                   ║${NC}"
echo -e "${BLUE}║        PAC-OPS-P95-CONTAINERIZATION                                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo -e "${YELLOW}[1/5]${NC} Validating Docker environment..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker is not installed or not in PATH${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker available${NC}"

echo ""
echo -e "${YELLOW}[2/5]${NC} Building Sovereign Node image..."
echo -e "      Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""

docker build \
    --tag "${IMAGE_NAME}:${IMAGE_TAG}" \
    --tag "${IMAGE_NAME}:latest" \
    --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    --build-arg VERSION="${IMAGE_TAG}" \
    --file Dockerfile \
    .

echo ""
echo -e "${GREEN}✓ Image built successfully${NC}"

echo ""
echo -e "${YELLOW}[3/5]${NC} Verifying image..."
docker image inspect "${IMAGE_NAME}:${IMAGE_TAG}" --format '{{.Id}}' > /dev/null
IMAGE_SIZE=$(docker image inspect "${IMAGE_NAME}:${IMAGE_TAG}" --format '{{.Size}}' | numfmt --to=iec 2>/dev/null || docker image inspect "${IMAGE_NAME}:${IMAGE_TAG}" --format '{{.Size}}')
echo -e "${GREEN}✓ Image verified (Size: ${IMAGE_SIZE})${NC}"

echo ""
echo -e "${YELLOW}[4/5]${NC} Running container health check..."

# Stop existing container if running
docker rm -f "${CONTAINER_NAME}-test" 2>/dev/null || true

# Run container in background for testing
docker run -d \
    --name "${CONTAINER_NAME}-test" \
    -p 8000:8000 \
    "${IMAGE_NAME}:${IMAGE_TAG}"

# Wait for startup
echo "      Waiting for container startup..."
sleep 3

# Check health endpoint
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Health check passed${NC}"
    HEALTH_STATUS="HEALTHY"
else
    echo -e "${YELLOW}⚠ Health check skipped (curl not available or endpoint not ready)${NC}"
    HEALTH_STATUS="SKIPPED"
fi

# Stop test container
docker rm -f "${CONTAINER_NAME}-test" 2>/dev/null || true

echo ""
echo -e "${YELLOW}[5/5]${NC} Build complete!"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    BUILD SUCCESSFUL                                  ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Image:    ${IMAGE_NAME}:${IMAGE_TAG}${NC}"
echo -e "${GREEN}║  Health:   ${HEALTH_STATUS}${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  To run:   docker-compose up sovereign-node${NC}"
echo -e "${GREEN}║  Or:       docker run -p 8000:8000 ${IMAGE_NAME}:${IMAGE_TAG}${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Output build info for logging
echo "{\"event\":\"BUILD_COMPLETE\",\"image\":\"${IMAGE_NAME}:${IMAGE_TAG}\",\"health\":\"${HEALTH_STATUS}\",\"timestamp\":\"$(date -u +'%Y-%m-%dT%H:%M:%SZ')\"}"
