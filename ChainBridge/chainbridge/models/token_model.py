"""Token persistence model."""

from __future__ import annotations

from sqlalchemy import JSON, Column, DateTime, String, func

from models.driver import Base

from chainbridge.tokens.serialization import deserialize, serialize


class TokenRecord(Base):
    """Generic table storing every LST-01 token instance."""

    __tablename__ = "tokens"

    id = Column(String, primary_key=True)
    token_type = Column(String, nullable=False, index=True)
    version = Column(String, nullable=False)
    state = Column(String, nullable=False)
    json_blob = Column(JSON, nullable=False)
    st01_root_id = Column(String, nullable=False, index=True)
    signature = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    @classmethod
    def from_token(cls, token, signature: str | None = None) -> "TokenRecord":
        payload = serialize(token)
        return cls(
            id=token.token_id,
            token_type=token.token_type,
            version=token.version,
            state=token.state,
            json_blob=payload,
            st01_root_id=token.parent_shipment_id,
            signature=signature,
        )

    def to_token(self):
        payload = dict(self.json_blob)
        payload.setdefault("token_id", self.id)
        payload.setdefault("type", self.token_type)
        payload.setdefault("version", self.version)
        payload.setdefault("state", self.state)
        return deserialize(payload)
