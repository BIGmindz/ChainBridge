# Black Formatting Standards for ChainBridge

## Overview

This document outlines the Black formatting issues found during CI/CD runs and how to fix them.

## Key Issues Identified

### 1. Blank Lines in Docstrings

**Problem**: Extra blank lines inside docstrings or between docstring and code

```python
# ❌ BEFORE
class Driver(Base):
    """
    Driver model description.

    """
    __tablename__ = "drivers"

# ✅ AFTER
class Driver(Base):
    """
    Driver model description.
    """
    __tablename__ = "drivers"
```

### 2. Blank Lines After Class Definitions

**Problem**: Missing blank line between class docstring and first attribute

```python
# ❌ BEFORE
class DriverBase(BaseModel):
    """Base driver schema with common fields."""
    first_name: str = Field(...)

# ✅ AFTER
class DriverBase(BaseModel):
    """Base driver schema with common fields."""

    first_name: str = Field(...)
```

### 3. Trailing Whitespace

**Problem**: Blank lines with trailing spaces

```python
# ❌ BEFORE
def function():
    """Docstring."""
    # (blank line with spaces below)
    return value

# ✅ AFTER
def function():
    """Docstring."""

    return value
```

### 4. Long Line Formatting

**Problem**: Long lines should be wrapped appropriately

```python
existing = db.query(DriverModel).filter(DriverModel.email == driver.email).first()
```

### 5. HTTPException Formatting

**Problem**: Multi-line HTTPException should be condensed when appropriate

```python
# ✅ PREFERRED
raise HTTPException(status_code=400, detail=f"Driver with email {driver.email} already exists")
```

### 6. Import Statements

**Problem**: Missing blank line before final imports

```python
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Files Affected

### ChainBoard Service

- `app/models.py`
- `app/main.py`
- `app/schemas.py`

### ChainFreight Service

- `app/chainiq_client.py`

### ChainPay Service

- ✅ Already Formatted (All Clear)

## How to Fix

### Automatic Format (Recommended)

```bash
black file.py
black ChainBridge/chainboard-service/
black ChainBridge/chainfreight-service/
```

### Validation

```bash
black --check ChainBridge/
black --diff ChainBridge/
```

## Integration with Pre-commit

The repository uses pre-commit hooks that automatically:

1. Fix end of file issues
2. Trim trailing whitespace
3. Format with Black

Run before committing:

```bash
pre-commit run --all-files
```

## Line Length

Black enforces a maximum line length of **88 characters** by default.

- Respect this limit in all code
- Use line continuation for long method chains
- Break function arguments across multiple lines if needed

## References

- [Black Documentation](https://black.readthedocs.io/)
- [Black Code Style](https://black.readthedocs.io/en/stable/the_black_code_style/index.html)
