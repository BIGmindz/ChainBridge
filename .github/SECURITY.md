# Security Policy

## Overview

Security is a top priority for the BIGmindz monorepo. This document outlines our security policies, vulnerability reporting procedures, and response timelines.

## 🛡️ Supported Versions

We provide security updates for the following versions:

| Product | Version | Supported |
|---------|---------|-----------|
| ChainBridge | Latest (main) | ✅ |
| ChainBridge | Previous release | ✅ |
| ChainBridge | Older versions | ❌ |
| BensonBot | Latest (main) | ✅ |
| BensonBot | Previous release | ✅ |
| BensonBot | Older versions | ❌ |

**Note**: We support the latest release on the `main` branch and the previous major release. Older versions receive no security updates.

## 🔒 Reporting a Vulnerability

### How to Report

**DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, use one of these secure methods:

#### Option 1: GitHub Security Advisories (Preferred)

1. Go to the [Security tab](https://github.com/BIGmindz/ChainBridge/security/advisories)
2. Click "Report a vulnerability"
3. Fill out the advisory form
4. Submit privately

#### Option 2: Direct Email

Email security concerns to:
- **Primary Contact**: [via GitHub @BIGmindz]
- **Subject Line**: `[SECURITY] Brief description`

### What to Include

Please provide:

1. **Description**: Clear description of the vulnerability
2. **Impact**: Potential impact and severity assessment
3. **Reproduction Steps**: Detailed steps to reproduce
4. **Proof of Concept**: Code or commands demonstrating the issue
5. **Affected Components**: Which product/service is affected
6. **Suggested Fix**: If you have ideas for mitigation
7. **Your Contact Info**: For follow-up questions

### Example Report

```markdown
## Vulnerability: SQL Injection in ChainPay Service

**Severity**: High

**Component**: ChainBridge/chainpay-service/app/payments.py

**Description**: 
The payment query endpoint is vulnerable to SQL injection through
the `invoice_id` parameter.

**Reproduction**:
1. Send POST request to `/api/payments/query`
2. Include payload: {"invoice_id": "1' OR '1'='1"}
3. Observe unauthorized data access

**Impact**:
Attacker can access all payment records in the database.

**Suggested Fix**:
Use parameterized queries instead of string concatenation.
```

## 📅 Response Timeline

### Initial Response

- **Acknowledgment**: Within 24 hours
- **Initial Assessment**: Within 48 hours
- **Regular Updates**: Every 72 hours until resolution

### Resolution Timeline by Severity

| Severity | Response Time | Patch Release |
|----------|--------------|---------------|
| **Critical** | Immediate (< 24h) | Within 7 days |
| **High** | < 48 hours | Within 7 days |
| **Medium** | < 1 week | Within 30 days |
| **Low** | < 2 weeks | Next release cycle |

### Severity Definitions

#### Critical
- Remote code execution
- Authentication bypass
- Data breach risk
- Complete system compromise

#### High
- Privilege escalation
- SQL injection
- Cross-site scripting (XSS)
- Sensitive data exposure

#### Medium
- Denial of service
- Information disclosure
- Weak cryptography
- CSRF vulnerabilities

#### Low
- Minor information leaks
- Configuration issues
- Non-security bugs with security implications

## 🔍 Security Scanning

### Automated Tools

We use the following security tools:

1. **CodeQL**: Semantic code analysis (GitHub Actions)
2. **Dependabot**: Dependency vulnerability scanning
3. **Bandit**: Python security linting
4. **Safety**: Python dependency security checking

### CI/CD Security Checks

All PRs must pass:
- CodeQL security analysis
- Dependency vulnerability scans
- Static security analysis
- Secret detection

## 📊 Dependabot Alerts

### Response Timelines

| Severity | Action Required | Timeline |
|----------|----------------|----------|
| **Critical** | Immediate update | Within 7 days |
| **High** | Priority update | Within 7 days |
| **Medium** | Scheduled update | Within 30 days |
| **Low** | Next sprint | Next sprint cycle |

### Dependabot Configuration

- **Auto-merge**: Enabled for minor/patch versions (after CI passes)
- **Manual review**: Required for major versions
- **Grouped updates**: Dependencies updated in batches when possible

### Handling Dependabot Alerts

1. **Review Alert**: Understand the vulnerability
2. **Assess Impact**: Determine if code is affected
3. **Test Update**: Verify update doesn't break functionality
4. **Deploy**: Merge and deploy fix
5. **Monitor**: Watch for issues post-deployment

## 🔐 Security Best Practices

### For Contributors

- **Never commit secrets**: Use `.env` files (already in `.gitignore`)
- **Use environment variables**: For API keys, passwords, tokens
- **Validate inputs**: Always validate and sanitize user inputs
- **Parameterized queries**: Never use string concatenation for SQL
- **Principle of least privilege**: Request minimum necessary permissions
- **Keep dependencies updated**: Regularly update to latest secure versions
- **Enable 2FA**: On GitHub and all critical services

### For ChainBridge

- **API Authentication**: All endpoints require authentication
- **Rate Limiting**: Implement rate limiting on public endpoints
- **Input Validation**: Validate all inputs server-side
- **Audit Logging**: Log all security-relevant events
- **ALEX Compliance**: Follow ALEX governance framework

### For BensonBot

- **API Key Security**: Store exchange API keys securely
- **Paper Trading First**: Always test with paper trading
- **Risk Limits**: Enforce position size and loss limits
- **Read-Only Keys**: Use read-only API keys where possible
- **Audit Trail**: Log all trades and decisions

## 🚨 Security Incidents

### If You Discover a Breach

1. **Do NOT** make the issue public
2. **Immediately contact** security team (see reporting section)
3. **Preserve evidence**: Save logs, screenshots, etc.
4. **Document timeline**: Record what happened when
5. **Follow guidance**: Wait for security team instructions

### Our Response Process

1. **Containment**: Isolate affected systems
2. **Assessment**: Determine scope and impact
3. **Eradication**: Remove vulnerability
4. **Recovery**: Restore secure operations
5. **Lessons Learned**: Post-incident review
6. **Disclosure**: Responsible public disclosure (if applicable)

## 📢 Disclosure Policy

### Responsible Disclosure

We follow a 90-day disclosure timeline:

1. **Day 0**: Vulnerability reported privately
2. **Day 0-7**: Initial assessment and acknowledgment
3. **Day 7-90**: Fix developed, tested, and deployed
4. **Day 90**: Public disclosure (if not fixed sooner)

### Coordinated Disclosure

If the vulnerability affects multiple systems or parties:
- We coordinate disclosure with affected parties
- We may extend the 90-day timeline if necessary
- We provide advance notice to affected users

### Public Disclosure

After a fix is deployed, we may publish:
- Security advisory
- CVE (if applicable)
- Technical details
- Mitigation steps

## 🏆 Security Researchers

### Recognition

We value security researchers and provide:
- **Public acknowledgment** (if desired) in security advisories
- **Credit in CHANGELOG** for significant findings
- **Security Hall of Fame** (coming soon)

### Bug Bounty

We currently do not offer a paid bug bounty program, but we:
- Deeply appreciate security reports
- Provide public recognition
- May offer swag or rewards for exceptional findings

## 🔧 Security Tooling

### For Developers

Install security tools:

```bash
# Python security tools
pip install bandit safety

# Run security checks
bandit -r . -f json -o bandit-report.json
safety check --json

# Pre-commit hooks (includes security checks)
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

### CI/CD Integration

Our CI automatically runs:
```bash
# Security audit (in trading-bot-ci.yml)
safety check || true
bandit -r . -f json -o bandit-report.json || true
```

## 📚 Additional Resources

### External Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)

### Internal Documentation

- [CONTRIBUTING.md](../CONTRIBUTING.md) - Security guidelines for contributors
- [ChainBridge Governance](../ChainBridge/docs/governance/) - ALEX framework
- [REPO_MAP.md](../docs/REPO_MAP.md) - Repository structure

## 📞 Contact

- **Security Issues**: [GitHub Security Advisories](https://github.com/BIGmindz/ChainBridge/security/advisories)
- **General Questions**: [GitHub Discussions](https://github.com/BIGmindz/ChainBridge/discussions)
- **Code Owner**: [@BIGmindz](https://github.com/BIGmindz)

---

## 📝 Version History

- **v1.0** (December 2024): Initial security policy

---

**Thank you for helping keep BIGmindz secure!** 🔒

Your responsible disclosure helps protect all users of ChainBridge and BensonBot.
