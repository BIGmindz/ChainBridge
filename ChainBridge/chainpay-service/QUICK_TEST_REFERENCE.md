<!-- markdownlint-disable MD032 MD031 -->

# Quick Reference: Running Tests & CI/CD

Fast commands for testing and validation.

## Local Development

### Run All Tests (Fast ⚡)
```bash
cd chainpay-service
python3 -m pytest tests/ -v
```

### Run All Tests with Coverage
```bash
cd chainpay-service
python3 -m pytest tests/ -v --cov=app --cov-report=html
# View report: open htmlcov/index.html
```

### Run Only E2E Tests
```bash
cd chainpay-service
python3 -m pytest tests/test_end_to_end_milestones.py -v
```

### Run Specific Test
```bash
cd chainpay-service
pytest tests/test_end_to_end_milestones.py::TestEndToEndFreightLifecycle::test_e2e_low_risk_freight_full_lifecycle -v
```

### Run Tests in Watch Mode
```bash
pip install pytest-watch
cd chainpay-service
ptw tests/test_end_to_end_milestones.py
```

### Check Coverage Percentage
```bash
cd chainpay-service
pytest tests/ --cov=app --cov-report=json
python3 -c "import json; cov=json.load(open('coverage.json')); print(f\"Coverage: {cov['totals']['percent_covered']:.1f}%\")"
```

## GitHub Actions (Automatic)

### Trigger CI/CD
Push to `main` or `develop`, or create a PR:
```bash
git push origin main
```

### View Test Results
``` text
https://github.com/BIGmindz/ChainBridge/actions/workflows/tests.yml
```

### View Coverage Report
``` text
https://codecov.io/gh/BIGmindz/ChainBridge
```

### Check PR Status
Pull requests automatically show:
- ✅ or ❌ badge next to commit
- Coverage percentage comment
- Link to full test results

## Debugging Failed Tests

### View Full Output
```bash
cd chainpay-service
pytest tests/test_end_to_end_milestones.py -v -s --tb=long
```

### Drop into Debugger
```bash
cd chainpay-service
pytest tests/test_end_to_end_milestones.py -v -s --pdb
```

### View Database State (in test)
```python
# Add to failing test
db_session.commit()
milestones = db_session.query(MilestoneSettlement).all()
print(f"Database has {len(milestones)} milestones")
for m in milestones:
    print(f"  {m.event_type}: ${m.amount} {m.status}")
```

## Common Issues

### Tests Pass Locally but Fail in CI?
1. Check Python version matches CI (3.11+):
   ```bash
   python3 --version
   ```
2. Clear cache and reinstall:
   ```bash
   cd chainpay-service
   rm -rf .pytest_cache
   pip install -r requirements.txt
   ```

### Coverage < 95%?
1. Generate HTML report:
   ```bash
   pytest --cov=app --cov-report=html
   ```
2. Open `htmlcov/index.html` and look for red lines (uncovered)
3. Add tests for those lines

### Import Errors?
```bash
cd chainpay-service
python3 -c "from app.models import PaymentIntent; print('OK')"
```

## Test Categories

| Category | File | Count | Type |
|----------|------|-------|------|
| Release Strategy | `test_should_release_now.py` | 32 | Unit |
| Schedule Builder | `test_schedule_builder.py` | 28 | Unit |
| Payment Rails | `test_payment_rails.py` | 45 | Unit |
| Audit Endpoints | `test_audit_endpoints.py` | 32 | Integration |
| Idempotency | `test_idempotency_stress.py` | 18 | Stress |
| End-to-End | `test_end_to_end_milestones.py` | 9 | E2E |
| **Total** | | **164** | |

## CI/CD Pipeline Status

### Current Workflows
``` text
.github/workflows/
├── ci.yml                   # Existing (trading bot)
├── trading-bot-ci.yml       # Existing (trading bot)
└── tests.yml               # ✨ NEW (ChainPay tests)
```

### Pipeline Stages (tests.yml)
1. ✅ Checkout
2. ✅ Setup Python (3.11 & 3.12)
3. ✅ Cache dependencies
4. ✅ Install packages
5. ✅ Lint code
6. ✅ Run tests
7. ✅ Check coverage (fail < 95%)
8. ✅ Upload to Codecov
9. ✅ Store artifacts
10. ✅ Comment on PR

### Expected Results
``` text
All tests pass: ✅
Coverage >= 95%: ✅
Build time: ~60 seconds (30-45 with cache)
```

## Files to Review

1. **Test Code:**
   - `chainpay-service/tests/test_end_to_end_milestones.py` (750 LOC)

2. **Documentation:**
   - `chainpay-service/TEST_END_TO_END.md` (400 LOC)
   - `chainpay-service/E2E_CICD_COMPLETE.md` (500 LOC)

3. **CI/CD:**
   - `.github/workflows/tests.yml` (150 LOC)

4. **Configuration:**
   - `chainpay-service/pytest.ini` (existing)
   - `README.md` (badges added)

## Tips & Tricks

### Run Tests Multiple Times (Check Consistency)
```bash
for i in {1..5}; do echo "Run $i:"; pytest tests/ -q; done
```

### Measure Test Execution Time
```bash
time pytest tests/ -q
```

### See Which Tests Run First/Last
```bash
pytest tests/ --collect-only -q
```

### Export Coverage as CSV
```bash
pytest --cov=app --cov-report=csv
cat coverage.csv
```

### Monitor Test Progress Live
```bash
# Terminal 1: Run tests
watch -n 1 'pytest tests/ -q'

# Terminal 2: Watch coverage
watch -n 1 'pytest --cov=app -q | tail -5'
```

## Integration with Development Flow

``` bash
# Normal development flow:
1. Make changes
2. Run tests locally:   pytest tests/ -v
3. Commit:             git commit -m "..."
4. Push:               git push origin feature-branch
5. Create PR
6. CI runs automatically (GitHub Actions)
7. See results on PR
8. Merge if all pass ✅
```

## External Links

- **GitHub Actions Workflow:** https://github.com/BIGmindz/ChainBridge/actions/workflows/tests.yml
- **Codecov Coverage:** https://codecov.io/gh/BIGmindz/ChainBridge
- **Repository:** https://github.com/BIGmindz/ChainBridge
- **Pytest Documentation:** https://docs.pytest.org/
- **GitHub Actions Docs:** https://docs.github.com/en/actions

---

**Quick Checklist Before Committing:**
- [ ] Run `pytest tests/ -v` locally (all pass)
- [ ] Check `pytest --cov=app -q` (coverage >= 95%)
- [ ] View `htmlcov/index.html` (looks good)
- [ ] No lint errors: `flake8 app/`
- [ ] Commit message is descriptive
- [ ] Push to feature branch first
- [ ] Create PR and wait for CI ✅

---

For detailed information, see:
- `TEST_END_TO_END.md` - Complete E2E test guide
- `TEST_SUITE.md` - All test documentation
- `E2E_CICD_COMPLETE.md` - Full implementation summary
