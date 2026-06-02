from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TimestampSchema(BaseSchema):
    created_at: datetime
    updated_at: datetime


class UUIDSchema(BaseSchema):
    id: uuid.UUID


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseSchema):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def build(cls, items: list, total: int, page: int, page_size: int) -> PaginatedResponse:
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )


class MessageResponse(BaseModel):
    message: str
    success: bool = True
