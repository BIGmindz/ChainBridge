# ChainBoard Service

Driver identity and onboarding API for the ChainBridge platform.

## Overview

ChainBoard is the identity layer of ChainBridge, responsible for:

- Driver registration and onboarding
- Driver profile management
- Driver verification and compliance tracking
- Enterprise identity (future)

## Tech Stack

- **Framework**: FastAPI
- **Database**: SQLAlchemy + SQLite (production: PostgreSQL)
- **Validation**: Pydantic
- **API Documentation**: OpenAPI (Swagger)

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Running the Service

```bash
# Development
python -m app.main

# Or directly
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

Visit `http://localhost:8000/docs` for interactive Swagger documentation.

## API Endpoints

### Health Check

```http
GET /health
```

Returns service status.

### Create Driver

```http
POST /drivers
Content-Type: application/json
```

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "phone": "555-1234",
  "dot_number": "DOT123456",
  "cdl_number": "CDL789012"
}
```

Response: `201 Created` with driver record.

### List Drivers

```http
GET /drivers?skip=0&limit=10&is_active=true
```

Returns paginated list of drivers with filtering options.

### Get Driver

```http
GET /drivers/{driver_id}
```

Returns a specific driver record.

### Update Driver

```http
PUT /drivers/{driver_id}
Content-Type: application/json
```

```json
{
  "first_name": "Jane",
  "phone": "555-5678"
}
```

Updates driver information (partial updates supported).

### Delete Driver

```http
DELETE /drivers/{driver_id}
```

Soft-deletes a driver (marks as inactive).

### Search Drivers

```http
GET /drivers/search?email=john@example.com&dot_number=DOT123456
```

Search drivers by email or DOT number (at least one required).

## Project Structure

``` text
chainboard-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app and routes
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   └── database.py          # DB session management
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Development

### Adding New Endpoints

1. Add database model to `models.py` if needed
2. Add Pydantic schema to `schemas.py`
3. Add route handler to `main.py`
4. Test via Swagger UI at `/docs`

### Database Migrations

Currently using SQLAlchemy's `Base.metadata.create_all()`. For production, integrate Alembic:

```bash
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Testing

```bash
# Create a test file
pytest tests/test_drivers.py

# Run all tests
pytest
```

## Environment Variables

Create a `.env` file:

```bash
DATABASE_URL=sqlite:///./chainboard.db
# For PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost/chainboard
```

## Future Enhancements

- [ ] Driver compliance and verification workflow
- [ ] Document upload and storage
- [ ] Background checks integration
- [ ] Two-factor authentication
- [ ] Rate limiting and API keys
- [ ] Event logging and audit trail
- [ ] Integration with ChainIQ for driver risk scoring
- [ ] Enterprise/organization support

## Contributing

Follow these patterns when extending ChainBoard:

1. **Type hints**: Always use full type hints
2. **Pydantic schemas**: Separate request/response models
3. **Dependency injection**: Use FastAPI's `Depends()` for DB sessions
4. **Error handling**: Return appropriate HTTP status codes
5. **Documentation**: Add docstrings to all functions

## License

Proprietary - ChainBridge Platform
