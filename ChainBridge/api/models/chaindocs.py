"""SQLAlchemy models for ChainDocs storage."""

import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from api.database import Base

# Ensure project root is on sys.path so `app.models` resolves in isolated test runs.
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from app.models.marketplace import Listing
except ModuleNotFoundError:
    import importlib.util
    import types

    app_pkg_path = project_root / "app"
    models_pkg_path = app_pkg_path / "models"

    if "app" not in sys.modules:
        app_pkg = types.ModuleType("app")
        app_pkg.__path__ = [str(app_pkg_path)]
        sys.modules["app"] = app_pkg

    if "app.models" not in sys.modules:
        models_pkg = types.ModuleType("app.models")
        models_pkg.__path__ = [str(models_pkg_path)]
        sys.modules["app.models"] = models_pkg

    spec = importlib.util.spec_from_file_location("app.models.marketplace", models_pkg_path / "marketplace.py")
    if spec is None or spec.loader is None:
        raise
    module = importlib.util.module_from_spec(spec)
    sys.modules["app.models.marketplace"] = module
    spec.loader.exec_module(module)
    Listing = module.Listing  # type: ignore[attr-defined]


class Shipment(Base):
    """Represents a shipment tracked by ChainDocs."""

    __tablename__ = "shipments"

    id = Column(String, primary_key=True, index=True)
    corridor_code = Column(String, nullable=True)
    mode = Column(String, nullable=True)
    incoterm = Column(String, nullable=True)
    staking_status = Column(String, nullable=True)
    collateral_value = Column(Float, nullable=True)
    loan_amount = Column(Float, nullable=True)
    current_audit_score = Column(Float, nullable=True)
    ricardian_hash = Column(String, nullable=True)
    listing = relationship("Listing", uselist=False, backref="shipment")

    documents = relationship(
        "Document",
        back_populates="shipment",
        cascade="all, delete-orphan",
    )


class DocumentType(Base):
    """Catalog of supported document types."""

    __tablename__ = "document_types"

    code = Column(String, primary_key=True, index=True)
    description = Column(String, nullable=False)
    mode = Column(String, nullable=True)
    direction = Column(String, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<DocumentType {self.code}>"


class ShipmentDocRequirement(Base):
    """Defines required/optional documents per shipment template or corridor."""

    __tablename__ = "shipment_doc_requirements"

    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String, nullable=False)
    corridor_code = Column(String, nullable=True)
    mode = Column(String, nullable=True)
    incoterm = Column(String, nullable=True)
    doc_type_code = Column(String, ForeignKey("document_types.code"), nullable=False)
    required_flag = Column(Boolean, nullable=False, default=True)
    blocking_flag = Column(Boolean, nullable=False, default=True)
    milestone_code = Column(String, nullable=True)

    doc_type = relationship("DocumentType")


class Document(Base):
    """Represents a document stored for a shipment."""

    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    shipment_id = Column(String, ForeignKey("shipments.id"), index=True, nullable=False)
    type = Column(String, index=True)
    status = Column(String, index=True)
    current_version = Column("version", Integer, default=1)
    hash = Column(String)
    latest_hash = Column(String, nullable=True)
    mletr = Column(Boolean, default=False)
    sha256_hex = Column(String, nullable=True)
    storage_backend = Column(String, nullable=True)
    storage_ref = Column(String, nullable=True)

    shipment = relationship("Shipment", back_populates="documents")


class DocumentVersion(Base):
    """Tracks each version update for a document."""

    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    hash = Column(String, nullable=True)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by_party = Column(String, nullable=True)
    source = Column(String, nullable=True)
    reason_code = Column(String, nullable=True)

    document = relationship("Document", backref="versions")
