# OCC v1.x Deployment Runbook

**PAC:** PAC-OCC-P06  
**Lane:** 3 — Ops & Deployment Hardening  
**Agent:** Dan (GID-07) — DevOps/CI Lead  
**Classification:** OPERATIONAL  
**Version:** 1.0.0

---

## Executive Summary

This runbook provides comprehensive operational procedures for deploying, monitoring, and maintaining the OCC (Operator Control Center) v1.x infrastructure. OCC is classified as **Critical Infrastructure** per PAC-JEFFREY-P04A.

---

## Pre-Deployment Checklist

### Environment Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| Python | 3.10+ | 3.11+ | Required for type hints |
| Memory | 2GB | 4GB+ | For audit log buffer |
| Storage | 10GB | 50GB+ | Audit log growth |
| CPU | 2 cores | 4+ cores | For concurrent requests |

### Dependencies

```bash
# Core dependencies
pip install fastapi uvicorn pydantic

# Cryptography (required for signing)
pip install pynacl  # Ed25519 signatures

# Database (production)
pip install sqlalchemy asyncpg  # PostgreSQL
# OR
pip install sqlalchemy aiosqlite  # SQLite (dev only)
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OCC_ENV` | No | `development` | Environment: development, staging, production |
| `OCC_API_HOST` | No | `0.0.0.0` | API bind address |
| `OCC_API_PORT` | No | `8000` | API port |
| `OCC_DATABASE_URL` | Yes (prod) | `sqlite:///occ.db` | Database connection string |
| `PROOFPACK_SIGNING_KEY` | Yes (prod) | - | Base64 Ed25519 private seed |
| `PROOFPACK_KEY_ID` | No | `pp-v1` | Signing key identifier |
| `OCC_AUDIT_SIGNING_KEY` | No | - | Audit entry signing key |
| `OCC_AUDIT_KEY_ID` | No | `audit-v1` | Audit key identifier |
| `OCC_AUDIT_REQUIRE_SIGNATURES` | No | `false` | Require signed audit entries |
| `OCC_LOG_LEVEL` | No | `INFO` | Logging level |

---

## Deployment Procedures

### Procedure: Fresh Deployment

**Time Estimate:** 30-45 minutes  
**Risk Level:** Medium  
**Requires:** T3+ operator authorization

#### Steps

1. **Verify Prerequisites**
   ```bash
   # Check Python version
   python --version  # Must be 3.10+
   
   # Check available memory
   free -h  # Linux
   vm_stat | perl -ne '/page size of (\d+)/ and $s=$1; /Pages (free|inactive):.*?(\d+)/ and print "$1: ".($2*$s/1024/1024)."MB\n"'  # macOS
   ```

2. **Generate Signing Keys**
   ```bash
   # Generate ProofPack signing key
   python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
   # Store securely - DO NOT commit to repository
   
   # Generate Audit signing key (optional)
   python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
   ```

3. **Configure Environment**
   ```bash
   # Copy template
   cp .env.example .env.production
   
   # Edit with production values
   vi .env.production
   ```

4. **Initialize Database**
   ```bash
   # Run migrations
   alembic upgrade head
   
   # Verify schema
   python -c "from core.occ.store import get_pdo_store; print('DB OK')"
   ```

5. **Start OCC Service**
   ```bash
   # Production start
   OCC_ENV=production uvicorn api.server:app \
     --host 0.0.0.0 \
     --port 8000 \
     --workers 4 \
     --log-level info
   ```

6. **Verify Health**
   ```bash
   curl http://localhost:8000/health
   # Expected: {"status": "healthy", ...}
   
   curl http://localhost:8000/api/v1/occ/status
   # Expected: {"kill_switch_active": false, ...}
   ```

7. **Record Deployment**
   - Log deployment in operational journal
   - Update deployment manifest
   - Notify on-call team

---

### Procedure: Rolling Update

**Time Estimate:** 15-30 minutes  
**Risk Level:** Low  
**Requires:** T2+ operator authorization

#### Steps

1. **Prepare Update**
   ```bash
   # Pull latest code
   git fetch origin
   git checkout release/v1.x.x
   
   # Verify tests pass
   pytest -q
   ```

2. **Drain Traffic (if using load balancer)**
   ```bash
   # Mark instance unhealthy
   curl -X POST http://localhost:8000/admin/drain
   
   # Wait for connections to close
   sleep 30
   ```

3. **Stop Current Instance**
   ```bash
   # Graceful shutdown
   kill -SIGTERM $(cat /var/run/occ.pid)
   
   # Wait for clean exit
   sleep 10
   ```

4. **Apply Update**
   ```bash
   # Install updated dependencies
   pip install -r requirements.txt
   
   # Run any migrations
   alembic upgrade head
   ```

5. **Start Updated Instance**
   ```bash
   OCC_ENV=production uvicorn api.server:app \
     --host 0.0.0.0 \
     --port 8000 \
     --workers 4
   ```

6. **Verify Update**
   ```bash
   # Check version
   curl http://localhost:8000/version
   
   # Check health
   curl http://localhost:8000/health
   ```

---

### Procedure: Emergency Rollback

**Time Estimate:** 5-10 minutes  
**Risk Level:** High  
**Requires:** T3+ operator authorization

#### Trigger Conditions
- Health check failures > 3 consecutive
- Error rate > 5% of requests
- P99 latency > 5 seconds
- Kill switch activated unexpectedly

#### Steps

1. **Assess Situation**
   ```bash
   # Check current state
   curl http://localhost:8000/health
   curl http://localhost:8000/api/v1/occ/status
   ```

2. **Stop Current Instance**
   ```bash
   kill -SIGKILL $(cat /var/run/occ.pid)
   ```

3. **Restore Previous Version**
   ```bash
   git checkout release/v1.x.x-previous
   pip install -r requirements.txt
   ```

4. **Restore Database (if needed)**
   ```bash
   # Only if schema changed
   alembic downgrade -1
   ```

5. **Start Restored Instance**
   ```bash
   OCC_ENV=production uvicorn api.server:app \
     --host 0.0.0.0 \
     --port 8000 \
     --workers 4
   ```

6. **Verify Restoration**
   ```bash
   curl http://localhost:8000/health
   ```

7. **Post-Incident**
   - File incident report
   - Schedule root cause analysis
   - Update runbook if needed

---

## Monitoring & Alerts

### Health Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Basic health check |
| `/health/ready` | GET | Readiness probe |
| `/health/live` | GET | Liveness probe |
| `/metrics` | GET | Prometheus metrics |

### Alert Definitions

#### Critical Alerts (Page On-Call)

| Alert | Condition | Action |
|-------|-----------|--------|
| `occ_down` | Health check fails 3x | Immediate investigation |
| `kill_switch_activated` | Kill switch state change | Verify intentional |
| `audit_chain_broken` | Hash chain verification fails | Forensic investigation |
| `signing_failure` | Ed25519 signing unavailable | Check key configuration |

#### Warning Alerts (Notify)

| Alert | Condition | Action |
|-------|-----------|--------|
| `high_latency` | P99 > 2 seconds | Investigate load |
| `queue_depth` | PDO queue > 1000 | Scale or investigate |
| `storage_low` | Disk < 20% free | Plan expansion |
| `error_rate` | Errors > 1% | Review logs |

### Prometheus Metrics

```yaml
# Key metrics to monitor
occ_pdo_total              # Total PDOs created
occ_pdo_by_state           # PDOs by state machine state
occ_audit_entries_total    # Total audit log entries
occ_proofpack_generated    # ProofPacks generated
occ_request_duration_seconds  # Request latency histogram
occ_kill_switch_active     # Boolean: kill switch state
```

---

## Backup & Recovery

### Audit Log Backup

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR=/backups/occ

# Export audit log
pg_dump -t audit_log $DATABASE_URL > $BACKUP_DIR/audit_$DATE.sql

# Verify backup
pg_restore --list $BACKUP_DIR/audit_$DATE.sql

# Encrypt and upload
gpg --encrypt --recipient ops@chainbridge.io $BACKUP_DIR/audit_$DATE.sql
aws s3 cp $BACKUP_DIR/audit_$DATE.sql.gpg s3://chainbridge-backups/occ/
```

### Recovery Procedure

1. **Identify Recovery Point**
   ```bash
   # List available backups
   aws s3 ls s3://chainbridge-backups/occ/
   ```

2. **Restore Backup**
   ```bash
   # Download and decrypt
   aws s3 cp s3://chainbridge-backups/occ/audit_$DATE.sql.gpg .
   gpg --decrypt audit_$DATE.sql.gpg > audit_$DATE.sql
   
   # Restore
   psql $DATABASE_URL < audit_$DATE.sql
   ```

3. **Verify Chain Integrity**
   ```bash
   python -c "
   from core.occ.crypto import get_evidence_verifier
   verifier = get_evidence_verifier()
   # Run verification...
   "
   ```

---

## Security Operations

### Key Rotation

**Frequency:** Quarterly or after suspected compromise

1. **Generate New Key**
   ```bash
   python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
   ```

2. **Update Configuration**
   - Update key in secret manager
   - Update `PROOFPACK_KEY_ID` to new version (e.g., `pp-v2`)

3. **Deploy with New Key**
   - New ProofPacks signed with new key
   - Old ProofPacks remain verifiable with old public key

4. **Archive Old Public Key**
   - Store in key archive for verification of historical ProofPacks

### Incident Response

1. **Detection**
   - Alert triggered or anomaly observed

2. **Containment**
   - Activate kill switch if needed
   - Isolate affected components

3. **Investigation**
   - Review audit logs
   - Check ProofPack integrity
   - Identify scope

4. **Recovery**
   - Apply fixes
   - Restore service
   - Verify integrity

5. **Post-Incident**
   - Document timeline
   - Root cause analysis
   - Update procedures

---

## Appendix

### A. Common Issues

| Issue | Symptoms | Resolution |
|-------|----------|------------|
| DB connection timeout | 500 errors | Check connection string, increase pool |
| Signing fails | ProofPack generation errors | Verify `PROOFPACK_SIGNING_KEY` |
| High memory | OOM kills | Increase memory, check for leaks |
| Slow queries | High latency | Add indexes, optimize queries |

### B. Contact Information

| Role | Contact | Hours |
|------|---------|-------|
| On-Call SRE | page@chainbridge.io | 24/7 |
| OCC Lead | occ-lead@chainbridge.io | Business |
| Security | security@chainbridge.io | 24/7 |

### C. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-05 | Dan (GID-07) | Initial runbook |

---

**Document Classification:** OPERATIONAL  
**Review Frequency:** Quarterly  
**Last Review:** 2026-01-05
