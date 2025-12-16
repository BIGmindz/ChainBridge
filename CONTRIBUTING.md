# Contributing to BIGmindz Monorepo

Thank you for your interest in contributing to the BIGmindz monorepo! This repository contains two distinct products: **ChainBridge** (freight platform) and **BensonBot** (trading bot). Please follow these guidelines to ensure smooth collaboration.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Branch Naming Conventions](#branch-naming-conventions)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)
- [Testing Requirements](#testing-requirements)
- [Code Quality Standards](#code-quality-standards)
- [CI/CD Scoping](#cicd-scoping)
- [Documentation](#documentation)

## 🤝 Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain professional communication
- Respect the monorepo structure (don't mix ChainBridge and BensonBot changes)

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- Code editor with EditorConfig support recommended

### Initial Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ChainBridge.git
   cd ChainBridge
   ```

2. **Set up for your product**

   **For ChainBridge:**
   ```bash
   cd ChainBridge
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

   **For BensonBot:**
   ```bash
   # Stay at root
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Verify your setup**
   ```bash
   # ChainBridge
   cd ChainBridge && pytest tests/ -v

   # BensonBot
   python benson_rsi_bot.py --test
   ```

## 🌿 Branch Naming Conventions

Use clear, descriptive branch names that indicate the product and purpose:

### ChainBridge Branches

```
feat/chainbridge-<description>     # New features
fix/chainbridge-<description>      # Bug fixes
docs/chainbridge-<description>     # Documentation
chore/chainbridge-<description>    # Maintenance tasks
test/chainbridge-<description>     # Test improvements
```

**Examples:**
- `feat/chainbridge-add-invoice-validation`
- `fix/chainbridge-payment-gateway-timeout`
- `docs/chainbridge-update-api-guide`

### BensonBot Branches

```
feat/bensonbot-<description>       # New features
fix/bensonbot-<description>        # Bug fixes
docs/bensonbot-<description>       # Documentation
chore/bensonbot-<description>      # Maintenance tasks
test/bensonbot-<description>       # Test improvements
```

**Examples:**
- `feat/bensonbot-add-sentiment-signal`
- `fix/bensonbot-rsi-calculation-edge-case`
- `docs/bensonbot-update-signal-docs`

### Cross-Product Branches

For changes affecting both products (rare):

```
feat/<description>                 # New features
fix/<description>                  # Bug fixes
docs/<description>                 # Documentation
chore/<description>                # Maintenance tasks
```

**Examples:**
- `docs/update-root-readme`
- `chore/update-python-version`
- `feat/add-unified-logging`

## 💬 Commit Message Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, semicolons, etc.)
- `refactor`: Code refactoring without feature changes
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks, dependencies
- `ci`: CI/CD changes
- `revert`: Reverting previous commits

### Scopes

- `chainbridge`: ChainBridge platform
- `chainiq`: ChainIQ service
- `chainpay`: ChainPay service
- `chainfreight`: ChainFreight service
- `bensonbot`: BensonBot trading system
- `signals`: Signal modules
- `regime`: Regime detection
- `risk`: Risk management
- `docs`: Documentation
- `ci`: CI/CD

### Examples

```bash
feat(bensonbot): add sentiment analysis signal module

Implements sentiment analysis signal using alternative data sources.
- Integrates with news APIs
- Calculates sentiment scores
- Low correlation with technical signals (0.05)

Closes #123

---

fix(chainpay): resolve payment gateway timeout issue

The payment gateway was timing out on large transactions due to
insufficient timeout settings. Increased timeout to 30s and added
retry logic with exponential backoff.

Fixes #456

---

docs(chainbridge): update service architecture diagram

Updated the architecture diagram to reflect new microservice
communication patterns.

---

test(bensonbot): add regime detection unit tests

Adds comprehensive unit tests for bull/bear/sideways regime detection.
Coverage increased to 95%.
```

## 📝 Pull Request Process

### 1. Create Your PR

Use the PR template (automatically loaded) and fill in ALL sections:

- **Description/Overview**: What problem does this solve?
- **Changes/Key Changes**: List specific changes
- **Evidence**: How do you know it works?
- **Risk**: What could go wrong? Impact assessment
- **Rollback**: How to undo if needed

### 2. PR Requirements

Your PR must meet these requirements to be merged:

#### ✅ Required Checks

- [ ] All CI checks pass
- [ ] All tests pass locally
- [ ] Code follows style guidelines (linting passes)
- [ ] Documentation updated (if applicable)
- [ ] No security vulnerabilities introduced
- [ ] At least one code owner approval
- [ ] No merge conflicts

#### 📋 PR Template Sections

All sections in the PR template must be completed:

1. **Description/Overview** - Clear problem statement
2. **Changes/Key Changes** - Bullet list of changes
3. **Evidence** - Test results, screenshots, metrics
4. **Risk** - Impact assessment (Low/Medium/High)
5. **Rollback** - Rollback procedure

### 3. Review Process

1. **Automated Checks**: CI runs automatically
2. **Code Owner Review**: Assigned automatically via CODEOWNERS
3. **Address Feedback**: Respond to review comments
4. **Approval**: At least one approval required
5. **Merge**: Squash and merge (preferred) or regular merge

### 4. After Merge

- Delete your feature branch
- Monitor deployment
- Verify changes in production/staging

## 🧪 Testing Requirements

### "Stop-the-Line" Policy

**All tests must pass before merge. No exceptions.**

If tests fail:
1. Fix the tests or code
2. If test is invalid, update/remove it (with justification)
3. Never disable or skip failing tests

### ChainBridge Testing

```bash
cd ChainBridge

# Run all tests
pytest tests/ -v

# Run specific service tests
pytest chainpay-service/tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Gatekeeper validation
python -m pytest tests/test_gatekeeper.py -v
```

### BensonBot Testing

```bash
# Built-in tests
python -m src.tests

# Full test suite (if pytest available)
pytest src/tests.py -v
pytest tests/ -v

# Specific test modules (if they exist)
pytest tests/test_signals.py -v

# Paper trading validation
python -m src.main --mode paper  # Let run for 24h
```

### Test Coverage Requirements

- **Minimum Coverage**: 70% for new code
- **Critical Paths**: 90%+ coverage required
- **Signal Modules**: 100% coverage required
- **ChainBridge Services**: 80%+ coverage required

### Writing Tests

```python
# Good test structure
def test_rsi_calculation_oversold():
    """Test RSI calculation identifies oversold conditions correctly."""
    # Arrange
    prices = [100, 95, 90, 85, 80, 75, 70]
    
    # Act
    rsi = calculate_rsi(prices)
    
    # Assert
    assert rsi < 35, f"Expected RSI < 35 for oversold, got {rsi}"
    assert rsi > 0, "RSI should be positive"
```

## 🎨 Code Quality Standards

### Python Style

- **Formatter**: Black (line length 120)
- **Linter**: Pylint, Flake8, Ruff
- **Type Hints**: Required for new code
- **Docstrings**: Required for all public functions

```python
def calculate_rsi(prices: list[float], period: int = 14) -> float:
    """
    Calculate RSI using Wilder's smoothing method.
    
    Args:
        prices: List of closing prices (most recent last)
        period: RSI period (default: 14)
    
    Returns:
        RSI value between 0 and 100
    
    Raises:
        ValueError: If insufficient price data
    """
    if len(prices) < period + 1:
        raise ValueError(f"Need at least {period + 1} prices")
    
    # Implementation...
    return rsi_value
```

### Code Review Checklist

Reviewers should verify:

- [ ] Code is readable and maintainable
- [ ] No hardcoded secrets or API keys
- [ ] Error handling is appropriate
- [ ] Logging is meaningful
- [ ] No unnecessary complexity
- [ ] Performance is acceptable
- [ ] Security best practices followed
- [ ] Tests are comprehensive

### Pre-Commit Hooks

We use pre-commit hooks to enforce quality:

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

Hooks include:
- Black formatting
- Flake8 linting
- Trailing whitespace removal
- YAML syntax validation
- Large file detection

## 🔄 CI/CD Scoping

### Path Filtering

Our CI is path-filtered to prevent cross-product contamination:

#### ChainBridge CI (`.github/workflows/ci.yml`)
Triggers on changes to:
- `ChainBridge/**`
- `.github/workflows/ci.yml`

#### BensonBot CI (`.github/workflows/trading-bot-ci.yml`)
Triggers on changes to:
- Root level trading files
- `src/**`, `modules/**`, `strategies/**`
- `tests/**` (BensonBot tests)
- `.github/workflows/trading-bot-ci.yml`

### Why Path Filtering?

- **Faster CI**: Only relevant tests run
- **Clearer Feedback**: Failures are product-specific
- **Resource Efficiency**: No wasted CI minutes
- **Better DX**: Developers see only relevant checks

### Cross-Product Changes

If your PR affects both products:
- **Both CIs will run** (expected and correct)
- **Both must pass** for merge
- Consider splitting into two PRs if possible

## 📚 Documentation

### When to Update Documentation

Update documentation when you:
- Add new features
- Change APIs or interfaces
- Modify configuration options
- Add new services or modules
- Change deployment procedures
- Fix significant bugs

### Documentation Locations

| Documentation | Location |
|---------------|----------|
| Root overview | `README.md` |
| ChainBridge | `ChainBridge/README.md` |
| BensonBot | `docs/bensonbot/README.md` |
| Repository map | `docs/REPO_MAP.md` |
| Service docs | `ChainBridge/*/README.md` |
| Governance | `ChainBridge/docs/governance/` |
| API docs | In-code docstrings |

### Documentation Standards

- Use clear, simple language
- Include code examples
- Add diagrams where helpful
- Keep READMEs up-to-date
- Link to related documentation
- Use consistent formatting

### Markdown Standards

- Use `markdownlint` for consistency
- Follow GitHub-flavored Markdown
- Use relative links for internal docs
- Include table of contents for long docs

## 🛠️ Development Workflow

### Typical Workflow

1. **Create Branch**
   ```bash
   git checkout -b feat/bensonbot-new-signal
   ```

2. **Make Changes**
   - Write code
   - Add tests
   - Update documentation

3. **Test Locally**
   ```bash
   # Run tests
   pytest tests/ -v
   
   # Run linting
   black --check .
   flake8 .
   
   # Run type checking
   mypy .
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat(bensonbot): add new sentiment signal"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feat/bensonbot-new-signal
   # Create PR on GitHub
   ```

6. **Address Review Feedback**
   ```bash
   # Make changes
   git add .
   git commit -m "fix: address review feedback"
   git push
   ```

7. **Merge**
   - Wait for approval
   - Squash and merge (preferred)

## 🔐 Security Guidelines

### Secrets Management

- **Never commit secrets** to version control
- Use `.env` files (already in `.gitignore`)
- Use environment variables
- Rotate API keys regularly

### Reporting Vulnerabilities

- Use [GitHub Security Advisories](https://github.com/BIGmindz/ChainBridge/security/advisories)
- See [SECURITY.md](.github/SECURITY.md) for full policy
- Do NOT open public issues for security vulnerabilities

### Security Best Practices

- Keep dependencies updated
- Address Dependabot alerts promptly (see timelines in SECURITY.md)
- Follow principle of least privilege
- Validate all inputs
- Use parameterized queries
- Enable 2FA on GitHub

## 🤔 Questions?

- **General Questions**: Open a [Discussion](https://github.com/BIGmindz/ChainBridge/discussions)
- **Bugs**: Open an [Issue](https://github.com/BIGmindz/ChainBridge/issues)
- **Security**: See [SECURITY.md](.github/SECURITY.md)
- **Documentation**: Check [REPO_MAP.md](docs/REPO_MAP.md)

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

**Thank you for contributing to BIGmindz!** 🙏

Your contributions help make ChainBridge and BensonBot better for everyone.
