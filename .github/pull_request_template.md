## Description / Overview
<!-- What problem does this solve? Why is this change needed? -->
<!-- Be specific and provide context for reviewers -->



## Changes / Key Changes
<!-- List the specific changes made in this PR -->
<!-- Use bullet points for clarity -->

- 
- 
- 

## Evidence
<!-- How do you know this works? Provide concrete evidence -->
<!-- Check all that apply and provide details -->

- [ ] Tests added/updated and passing
- [ ] Manual testing completed
- [ ] Documentation updated
- [ ] Screenshots/videos attached (for UI changes)
- [ ] Performance benchmarks (if applicable)

### Test Results

**ChainBridge Tests** (if applicable):
```bash
cd ChainBridge && pytest tests/ -v
python -m pytest tests/test_gatekeeper.py -v
```

**BensonBot Tests** (if applicable):
```bash
python benson_rsi_bot.py --test
pytest tests/ -k trading -v
```

**Test Output:**
```
# Paste relevant test output here
```

### Manual Testing

<!-- Describe manual testing performed -->



## Risk
<!-- What could go wrong? Be honest and thorough -->
<!-- Consider: breaking changes, performance impact, security implications -->

**Risk Level**: [Low / Medium / High]

**Potential Issues:**
- 

**Impact Assessment:**
- **Users**: 
- **Systems**: 
- **Data**: 

**Mitigation Strategies:**
- 

## Rollback
<!-- How do we undo this if needed? Provide clear rollback steps -->

**Rollback Procedure:**
1. 
2. 
3. 

**Recovery Time Estimate**: 

**Data Considerations**: 
<!-- Will any data need to be restored? How? -->

---

## Checklist

<!-- Verify you've completed all required items -->

### Code Quality
- [ ] Code follows project style guidelines
- [ ] Linting passes (Black, Flake8, Pylint)
- [ ] Type hints added (if Python)
- [ ] No hardcoded secrets or API keys
- [ ] Error handling is appropriate
- [ ] Logging is meaningful

### Testing
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Edge cases covered
- [ ] Test coverage meets requirements (70%+ for new code)

### Documentation
- [ ] README updated (if needed)
- [ ] API documentation updated (if needed)
- [ ] Inline code comments added for complex logic
- [ ] CHANGELOG updated (if applicable)

### CI/CD
- [ ] CI checks pass
- [ ] No cross-product contamination (ChainBridge changes don't affect BensonBot CI, and vice versa)
- [ ] Security scans pass

### Product-Specific

**ChainBridge PRs:**
- [ ] Gatekeeper validation passes
- [ ] ALEX governance compliance verified
- [ ] Service-specific tests pass
- [ ] No breaking changes to other services (or documented)

**BensonBot PRs:**
- [ ] Paper trading validation completed (if trading logic changed)
- [ ] Signal correlation maintained < 0.30 (if new signal added)
- [ ] RSI thresholds remain canonical (BUY=35, SELL=64)
- [ ] Risk management not weakened

### Security
- [ ] No sensitive data exposed
- [ ] Dependencies scanned for vulnerabilities
- [ ] Security best practices followed
- [ ] Secrets in environment variables only

---

## Additional Notes

<!-- Any other information reviewers should know -->
<!-- Link related issues, PRs, or discussions -->

**Related Issues:**
- Closes #
- Relates to #

**Related PRs:**
- Depends on #
- Follows up #

**Breaking Changes:**
<!-- If yes, describe migration path -->
- [ ] This PR contains breaking changes

**Future Work:**
<!-- What's intentionally deferred? -->



---

## Reviewer Guidelines

**For Code Owners:**
- Verify all checklist items are complete
- Check that tests are meaningful and comprehensive
- Ensure documentation is clear and accurate
- Validate risk assessment is realistic
- Confirm rollback procedure is viable

**Security Review:**
- [ ] No secrets in code
- [ ] Input validation present
- [ ] Authentication/authorization correct
- [ ] Dependency vulnerabilities addressed

**Performance Review:**
- [ ] No obvious performance regressions
- [ ] Resource usage reasonable
- [ ] Scalability considered

---

**Thank you for your contribution!** 🎉
