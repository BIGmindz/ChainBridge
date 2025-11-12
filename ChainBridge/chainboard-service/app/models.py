"""
Database models for ChainBoard Service.

This module contains SQLAlchemy models for driver identity and onboarding.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Driver(Base):
    """
    Driver model for managing transportation and logistics drivers.
    
    This model tracks driver information including personal details,
    contact information, regulatory identifiers, and onboarding status.
    """
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    dot_number = Column(String, nullable=True, comment="Department of Transportation number")
    cdl_number = Column(String, nullable=True, comment="Commercial Driver's License number")
    
    # Status tracking
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Driver(id={self.id}, name='{self.first_name} {self.last_name}', email='{self.email}')>"

    @property
    def full_name(self) -> str:
        """Return the driver's full name."""
        return f"{self.first_name} {self.last_name}"
