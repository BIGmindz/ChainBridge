"""
ChainBoard Service (ChainBridge)

Goal:
- Provide an API for driver identity and onboarding.
- Expose endpoints to create and fetch driver records.
- Use SQLAlchemy and SQLite (for now) for persistence.
- This is the MVP for the ChainBridge 'identity layer'.

Tasks for Copilot:
- Keep endpoints simple: POST /drivers, GET /drivers, GET /drivers/{id}.
- Use Pydantic models for request/response schemas.
- Use dependency-injected DB sessions.
- Make the code clean, explicit, and easy to extend (we'll add compliance checks later).
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .database import get_db, init_db
from .models import Driver as DriverModel
from .schemas import (
    DriverCreate,
    DriverUpdate,
    DriverResponse,
    DriverListResponse,
)

app = FastAPI(
    title="ChainBoard Service",
    description="Driver identity and onboarding API for ChainBridge",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "chainboard"}


@app.post("/drivers", response_model=DriverResponse, status_code=201)
async def create_driver(
    driver: DriverCreate,
    db: Session = Depends(get_db),
) -> DriverResponse:
    """
    Create a new driver record.

    Args:
        driver: Driver information to create
        db: Database session

    Returns:
        Created driver record

    Raises:
        HTTPException: If email already exists
    """
    # Check if driver with this email already exists
    existing = db.query(DriverModel).filter(DriverModel.email == driver.email).first()

    if existing:
        raise HTTPException(status_code=400, detail=f"Driver with email {driver.email} already exists")

    # Create new driver
    db_driver = DriverModel(**driver.model_dump())
    db.add(db_driver)
    db.commit()
    db.refresh(db_driver)

    return db_driver


@app.get("/drivers", response_model=DriverListResponse)
async def list_drivers(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    is_active: bool | None = Query(None),
    db: Session = Depends(get_db),
) -> DriverListResponse:
    """
    List drivers with optional filtering.

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        is_active: Filter by active status (optional)
        db: Database session

    Returns:
        List of drivers with total count
    """
    query = db.query(DriverModel)

    # Apply status filter if provided
    if is_active is not None:
        query = query.filter(DriverModel.is_active == is_active)

    total = query.count()
    drivers = query.offset(skip).limit(limit).all()

    return DriverListResponse(total=total, drivers=drivers)


@app.get("/drivers/{driver_id}", response_model=DriverResponse)
async def get_driver(
    driver_id: int,
    db: Session = Depends(get_db),
) -> DriverResponse:
    """
    Retrieve a specific driver by ID.

    Args:
        driver_id: ID of the driver to retrieve
        db: Database session

    Returns:
        Driver record

    Raises:
        HTTPException: If driver not found
    """
    driver = db.query(DriverModel).filter(DriverModel.id == driver_id).first()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    return driver


@app.put("/drivers/{driver_id}", response_model=DriverResponse)
async def update_driver(
    driver_id: int,
    driver_update: DriverUpdate,
    db: Session = Depends(get_db),
) -> DriverResponse:
    """
    Update a driver's information.

    Args:
        driver_id: ID of the driver to update
        driver_update: Fields to update
        db: Database session

    Returns:
        Updated driver record

    Raises:
        HTTPException: If driver not found
    """
    driver = db.query(DriverModel).filter(DriverModel.id == driver_id).first()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    # Update only provided fields
    update_data = driver_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(driver, field, value)

    db.add(driver)
    db.commit()
    db.refresh(driver)

    return driver


@app.delete("/drivers/{driver_id}", status_code=204)
async def delete_driver(
    driver_id: int,
    db: Session = Depends(get_db),
):
    """
    Soft-delete a driver (mark as inactive).

    Args:
        driver_id: ID of the driver to delete
        db: Database session

    Raises:
        HTTPException: If driver not found
    """
    driver = db.query(DriverModel).filter(DriverModel.id == driver_id).first()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    driver.is_active = False
    db.add(driver)
    db.commit()


@app.get("/drivers/search")
async def search_drivers(
    email: str | None = Query(None),
    dot_number: str | None = Query(None),
    db: Session = Depends(get_db),
) -> DriverListResponse:
    """
    Search for drivers by email or DOT number.

    Args:
        email: Email to search for (optional)
        dot_number: DOT number to search for (optional)
        db: Database session

    Returns:
        List of matching drivers

    Raises:
        HTTPException: If no search criteria provided
    """
    if not email and not dot_number:
        raise HTTPException(status_code=400, detail="At least one search parameter (email or dot_number) is required")

    query = db.query(DriverModel).filter(DriverModel.is_active)

    filters = []
    if email:
        filters.append(DriverModel.email == email)
    if dot_number:
        filters.append(DriverModel.dot_number == dot_number)

    if filters:
        query = query.filter(*[f for f in filters])

    drivers = query.all()

    return DriverListResponse(total=len(drivers), drivers=drivers)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
