# Staging Pipeline Documentation — PAC-DAN-031

> **Author**: DAN (GID-04) DevOps & CI/CD Lead
> **Status**: Active
> **Last Updated**: 2025-01-XX
> **Workflow**: `deploy-staging.yml`

---

## 📋 Overview

The staging pipeline automates deployment to the staging environment, including Docker image building, integration testing, and health verification.

### Pipeline Flow

```
┌─────────────────┐
│ pre-deploy-checks│
└────────┬────────┘
         │
   ┌─────┴─────────────────────┐
   │                           │
   ▼           ▼               ▼
┌──────┐  ┌──────┐      ┌─────────┐
│chainiq│  │chainpay│      │ gateway │
│ build │  │ build │      │  build  │
└───┬───┘  └───┬───┘      └────┬────┘
    │          │               │
    └──────────┴───────────────┘
                    │
                    ▼
         ┌───────────────────┐
         │ integration-tests │
         └─────────┬─────────┘
                   │
                   ▼
         ┌───────────────────┐
         │  deploy-staging   │
         └─────────┬─────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
         ▼                   ▼
┌─────────────┐     ┌─────────────┐
│register-models│     │ smoke-tests │
└──────┬──────┘     └──────┬──────┘
       │                   │
       └─────────┬─────────┘
                 │
                 ▼
         ┌─────────────┐
         │ notify-alex │
         └─────────────┘
```

---

## 🔧 Trigger Configuration

### Automatic Triggers

```yaml
on:
  push:
    branches: [develop]
```

Automatic deployment occurs when:
- Code is pushed to the `develop` branch
- All CI checks have passed

### Manual Dispatch

```yaml
workflow_dispatch:
  inputs:
    deploy_environment:
      description: 'Target environment'
      default: 'staging'
    skip_tests:
      description: 'Skip integration tests'
      default: 'false'
    force_rebuild:
      description: 'Force rebuild all images'
      default: 'false'
```

---

## 🐳 Docker Images

### Image Registry

All images are pushed to GitHub Container Registry:

```
ghcr.io/bigmindz/chainbridge/
```

### Image Tags

**Staging Tags** (automatic):
```
ghcr.io/bigmindz/chainbridge/chainiq:staging-20250115-abc1234
ghcr.io/bigmindz/chainbridge/chainpay:staging-20250115-def5678
ghcr.io/bigmindz/chainbridge/gateway:staging-20250115-ghi9012
```

**Latest Tags** (updated on each staging deploy):
```
ghcr.io/bigmindz/chainbridge/chainiq:staging-latest
ghcr.io/bigmindz/chainbridge/chainpay:staging-latest
ghcr.io/bigmindz/chainbridge/gateway:staging-latest
```

### Build Context

| Service | Dockerfile | Context |
|---------|-----------|---------|
| ChainIQ | `chainiq-service/Dockerfile` | `./chainiq-service` |
| ChainPay | `chainpay-service/Dockerfile` | `./chainpay-service` |
| Gateway | `Dockerfile` | `.` |

---

## 🧪 Integration Tests

### Test Suite

Integration tests run against ephemeral services:

```yaml
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_DB: chainbridge_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test

  redis:
    image: redis:7
```

### Test Categories

| Category | Description | Timeout |
|----------|-------------|---------|
| API Health | Endpoint availability | 60s |
| Database | Schema migrations | 120s |
| Cross-Service | Service communication | 180s |
| Performance | Response time benchmarks | 300s |

### Running Locally

```bash
# Start test infrastructure
docker compose -f docker-compose.test.yml up -d

# Run integration tests
pytest tests/integration/ -v --tb=short

# Cleanup
docker compose -f docker-compose.test.yml down -v
```

---

## 🚀 Deployment Process

### Step 1: Pre-Deploy Checks

```yaml
pre-deploy-checks:
  runs-on: ubuntu-latest
  outputs:
    deploy_version: ${{ steps.version.outputs.version }}
  steps:
    - name: Validate deployment readiness
      run: |
        # Check CI status
        # Verify no blocking issues
        # Generate deployment version
```

### Step 2: Build Images

Parallel build using Docker Buildx:

```yaml
- uses: docker/build-push-action@v5
  with:
    context: ./chainiq-service
    push: true
    tags: |
      ghcr.io/bigmindz/chainbridge/chainiq:${{ needs.pre-deploy.outputs.version }}
      ghcr.io/bigmindz/chainbridge/chainiq:staging-latest
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### Step 3: Deploy to Staging

```yaml
deploy-staging:
  runs-on: ubuntu-latest
  environment: staging
  steps:
    - name: Deploy to staging server
      env:
        SSH_KEY: ${{ secrets.STAGING_SSH_KEY }}
        STAGING_HOST: ${{ secrets.STAGING_HOST }}
      run: |
        # SSH to staging server
        # Pull new images
        # Rolling update with docker compose
```

### Step 4: Health Verification

```yaml
smoke-tests:
  runs-on: ubuntu-latest
  steps:
    - name: Wait for deployment
      run: sleep 30

    - name: Health checks
      run: |
        curl -f https://staging.chainbridge.io/health
        curl -f https://staging.chainbridge.io/api/v1/status
```

---

## 🔐 Secrets Configuration

### Required Secrets

| Secret | Description | Where to Get |
|--------|-------------|--------------|
| `GHCR_PAT` | GitHub Container Registry token | GitHub Settings > Developer Settings > PAT |
| `STAGING_SSH_KEY` | SSH private key for staging server | Generate with `ssh-keygen` |
| `STAGING_HOST` | Staging server hostname | Infrastructure team |
| `STAGING_USER` | SSH username | Infrastructure team |

### Setting Secrets

```bash
# Using GitHub CLI
gh secret set GHCR_PAT --body "ghp_xxxxxxxxxxxx"
gh secret set STAGING_SSH_KEY < ~/.ssh/staging_deploy_key
```

---

## 📊 Deployment Versioning

### Version Format

```
staging-YYYYMMDD-<git-short-sha>
```

Example: `staging-20250115-abc1234`

### Model Version Registration

After deployment, models are registered with their versions:

```yaml
register-models:
  steps:
    - name: Register model versions
      run: |
        python scripts/register_models.py \
          --version ${{ needs.pre-deploy.outputs.version }} \
          --environment staging
```

---

## 🔄 Rollback Procedure

### Automatic Rollback

If smoke tests fail, automatic rollback is triggered:

```yaml
- name: Rollback on failure
  if: failure()
  run: |
    # Get previous version
    PREV_VERSION=$(curl -s staging.chainbridge.io/version)

    # Deploy previous version
    docker compose pull
    docker compose up -d
```

### Manual Rollback

```bash
# List available versions
docker images ghcr.io/bigmindz/chainbridge/chainiq --format "{{.Tag}}"

# Deploy specific version
export VERSION=staging-20250114-xyz9876
docker compose -f docker-compose.staging.yml up -d
```

---

## 📈 Monitoring

### Deployment Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| Deploy Duration | Total pipeline time | > 15 minutes |
| Image Size | Docker image size | > 1 GB |
| Smoke Test Time | Health check duration | > 60 seconds |
| Rollback Rate | Failed deployments | > 10% |

### Dashboards

- **GitHub Actions**: Workflow run history
- **Staging Metrics**: `https://staging.chainbridge.io/metrics`
- **ALEX Dashboard**: Agent deployment notifications

---

## 🛠 Local Testing

### Simulate Staging Deploy

```bash
# Build images locally
make build

# Start staging simulation
make staging

# Or manually:
docker compose -f docker-compose.staging.yml up -d

# View logs
docker compose -f docker-compose.staging.yml logs -f
```

### Test Integration Locally

```bash
# Start test services
docker compose -f docker-compose.test.yml up -d

# Run integration tests
pytest tests/integration/ -v

# Cleanup
docker compose -f docker-compose.test.yml down -v
```

---

## 🚨 Troubleshooting

### Build Failures

**"Cannot connect to Docker daemon"**
```bash
# Ensure Docker is running
docker info

# Check GitHub Actions runner
# Self-hosted runners need Docker installed
```

**"Permission denied pushing to ghcr.io"**
```bash
# Verify PAT has correct scopes:
# - read:packages
# - write:packages
# - delete:packages

# Re-authenticate:
echo $GHCR_PAT | docker login ghcr.io -u USERNAME --password-stdin
```

### Deployment Failures

**"SSH connection refused"**
```bash
# Verify SSH key is correct
ssh -i staging_key staging_user@staging_host

# Check firewall rules
# Verify security group allows port 22
```

**"Health check failed"**
```bash
# SSH to staging and check logs
docker compose logs chainiq
docker compose logs chainpay

# Check service health
docker compose ps
```

---

## 📚 Related Documentation

- [CI_OVERVIEW.md](./CI_OVERVIEW.md) — CI workflow documentation
- [../RSI_THRESHOLD_POLICY.md](../RSI_THRESHOLD_POLICY.md) — Trading thresholds
- [../../docker-compose.staging.yml](../../docker-compose.staging.yml) — Staging compose config
