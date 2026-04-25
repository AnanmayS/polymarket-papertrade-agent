"""Shared Pydantic schema helpers."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Base schema with SQLAlchemy compatibility."""

    model_config = ConfigDict(from_attributes=True)


class TimeStamped(ORMModel):
    """Schema mixin for created/updated dates."""

    created_at: datetime
    updated_at: datetime
