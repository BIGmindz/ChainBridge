# Enterprise Trading Bot v2.0

## Production-grade cryptocurrency trading system with enterprise observability, secrets management, and high availability

## 🚀 Quick Start

### Prerequisites

- Python 3.11+

- Docker (optional)

- Kubernetes cluster (for production deployment)

- HashiCorp Vault or AWS Secrets Manager (recommended)

### Local Development

```bash

## Install dependencies

pip install -r requirements-enterprise.txt

## Run preflight checks

python src/bot/main.py --preflight

## Paper trading (single cycle)

python src/bot/main.py --mode paper --once

## Paper trading (continuous)

python src/bot/main.py --mode paper

## Live trading (requires confirmation)

python src/bot/main.py --mode live --confirm

```text

### Docker

```bash

## Build image

docker build -f Dockerfile.enterprise -t trading-bot:latest .

## Run with paper trading

docker run -e MODE=paper trading-bot:latest

## Run with environment file

docker run --env-file .env trading-bot:latest python src/bot/main.py --mode paper --once

```text

### Kubernetes Deployment

```bash

## Apply manifests

kubectl apply -f k8s/deployment.yaml

## Check status

kubectl get pods -n trading-bot
kubectl logs -f deployment/trading-bot -n trading-bot

## Access metrics

kubectl port-forward svc/trading-bot 9090:9090 -n trading-bot
open http://localhost:9090/metrics

```text

## 🏗️ Architecture

### Enterprise Components

1. **Resilient Data Fetcher** (`src/bot/core/resilient_data_fetcher.py`)

   - Circuit breaker pattern

   - Exponential backoff for rate limits (handles 429 errors)

   - Intelligent caching with TTL

   - Request deduplication

   - Graceful degradation to fallback values

1. **Secrets Manager** (`src/bot/core/secrets_manager.py`)

   - Multi-provider support (Vault, AWS Secrets Manager, Environment)

   - Automatic rotation tracking

   - Audit logging (all secret access logged)

   - Secret metadata (access count, last rotation)

1. **Observability Stack** (`src/bot/core/observability.py`)

   - Structured JSON logging (ELK-ready)

   - Prometheus metrics (orders, latency, P&L, signals)

   - Request tracing

   - Performance measurement decorators

1. **Canonical Entry Point** (`src/bot/main.py`)

   - Unified bot orchestrator

   - Lifecycle management

   - Health checks

   - Graceful shutdown

### Metrics Exposed

```text

## Trading metrics

bot_orders_total{side, symbol, status}
bot_order_latency_seconds
bot_capital_utilization_pct
bot_realized_pnl_usd
bot_unrealized_pnl_usd
bot_active_positions

## Signal metrics

bot_signal_generation_seconds{module}
bot_signal_confidence{module, signal_type}
bot_signal_errors_total{module, error_type}

## System health

bot_exchange_api_errors_total{exchange, endpoint, status_code}
bot_circuit_breaker_state{endpoint}
bot_data_source_status{source}

```text

## 🔒 Security

### Secrets Management

#### Option 1: HashiCorp Vault (Recommended)

```bash

export VAULT_ADDR=https://vault.yourdomain.com
export VAULT_TOKEN=your-token-here

python src/bot/main.py --mode live --confirm

```text

#### Option 2: AWS Secrets Manager

```bash

export AWS_REGION=us-east-1

## AWS credentials from IAM role or ~/.aws/credentials

python src/bot/main.py --mode live --confirm

```text

### Option 3: Environment Variables (Development Only)

```bash

export API_KEY=your-api-key
export API_SECRET=your-api-secret

python src/bot/main.py --mode paper --once

```text

### Secret Rotation

```bash

## Check rotation status

python src/bot/main.py --preflight

## Secrets are automatically checked for rotation (default: 30 days)

## All access is logged to logs/audit/secrets_audit.jsonl

```text

## 📊 Monitoring

### Prometheus Integration

```yaml

## Add to prometheus.yml

scrape_configs:

  - job_name: 'trading-bot'
    static_configs:

      - targets: ['trading-bot:9090']
    scrape_interval: 30s

```text

### Grafana Dashboard

Import the provided dashboard:

```bash

## Coming soon: grafana-dashboard.json

```text

### Log Aggregation

Structured logs are written to `logs/trading-bot.jsonl` in JSON format:

```json

{
  "timestamp": "2025-10-06T10:30:00.000Z",
  "level": "info",
  "message": "Trade executed",
  "symbol": "BTC/USD",
  "side": "buy",
  "amount": 0.01,
  "price": 45000.0,
  "order_id": "ORDER-123",
  "status": "filled"
}

```text

## 🧪 Testing

### Run Tests

```bash

## All tests

pytest tests/ -v

## With coverage

pytest tests/ --cov=src --cov-report=html

## Specific test file

pytest tests/test_resilient_fetcher.py -v

```text

### Quality Checks

```bash

## Code formatting

black src/ tests/

## Linting

flake8 src/ tests/ --max-line-length=100

## Type checking

mypy src/bot/ --ignore-missing-imports

## Security scan

bandit -r src/ -f json
safety check

```text

## 🚢 Deployment

### CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/enterprise-ci-cd.yml`) provides:

- ✅ Automated testing on every PR

- ✅ Security scanning (Snyk, Bandit, Trivy)

- ✅ Docker image building and pushing

- ✅ Automated staging deployment

- ✅ Manual approval for production

- ✅ Blue/green deployment strategy

- ✅ Automatic rollback on failure

### Production Deployment Checklist

- [ ] Configure secrets in Vault/AWS Secrets Manager

- [ ] Set up Prometheus scraping

- [ ] Configure Grafana dashboards

- [ ] Set up ELK stack for log aggregation

- [ ] Configure PagerDuty/Slack alerts

- [ ] Test disaster recovery procedures

- [ ] Run security audit

- [ ] Conduct load testing

- [ ] Update runbooks

## 📖 Configuration

### Command-Line Options

```text

--mode {live|paper}          Trading mode (default: paper)
--confirm                    Confirm live trading (required for live mode)
--once                       Run single cycle then exit
--min-confidence FLOAT       Minimum signal confidence (default: 0.25)
--metrics-port INT           Prometheus metrics port (default: 9090)
--preflight                  Run validation checks only

```text

### Environment Variables

```bash

## Secrets management

VAULT_ADDR                   Vault server address
VAULT_TOKEN                  Vault authentication token
VAULT_ROLE_ID                Vault AppRole ID
AWS_REGION                   AWS region for Secrets Manager

## Bot configuration

MODE                         Trading mode (live/paper)
METRICS_PORT                 Metrics server port
MIN_CONFIDENCE               Minimum signal confidence
LOG_LEVEL                    Logging level (DEBUG/INFO/WARNING/ERROR)

## Exchange credentials (if not using Vault/AWS)

API_KEY / KRAKEN_API_KEY     Exchange API key
API_SECRET / KRAKEN_SECRET   Exchange API secret

```text

## 🐛 Troubleshooting

### Common Issues

**Issue**: Rate limiting (429 errors) from external APIs

**Solution**: Circuit breaker automatically handles this. Check circuit breaker state:

```bash

curl http://localhost:9090/metrics | grep circuit_breaker_state

```text

**Issue**: Missing credentials

**Solution**: Verify secrets configuration:

```bash

python src/bot/main.py --preflight

```text

**Issue**: Data source failures

**Solution**: Bot automatically degrades gracefully. Check data source health:

```bash

curl http://localhost:9090/metrics | grep data_source_status

```text

### Debug Mode

```bash

## Enable verbose logging

export LOG_LEVEL=DEBUG
python src/bot/main.py --mode paper --once

```text

## 📚 Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)

- [Operations Runbook](docs/RUNBOOK.md)

- [Security Best Practices](docs/SECURITY.md)

- [Disaster Recovery](docs/DISASTER_RECOVERY.md)

- [API Documentation](docs/API.md)

## 🔄 Migration from Legacy Bot

**Deprecation Notice**: Legacy entry points (`live_trading_bot.py`, `multi_signal_bot.py`, `benson_rsi_bot.py`) are deprecated and will be removed in v3.0.

### Migration Steps

1. Update scripts to use new entry point:

   ```bash

## Old

   python live_trading_bot.py

## New

   python src/bot/main.py --mode live --confirm

   ```

1. Configure secrets management (remove hardcoded credentials)

1. Update monitoring to use Prometheus metrics

1. Test in paper mode first

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## 📄 License

See [LICENSE](LICENSE) for details.

## 🆘 Support

- GitHub Issues: [Report a bug](https://github.com/BIGmindz/Multiple-signal-decision-bot/issues)

- Documentation: [Wiki](https://github.com/BIGmindz/Multiple-signal-decision-bot/wiki)

---

## Built with ❤️ by the BIGmindz team

Last Updated: October 6, 2025
