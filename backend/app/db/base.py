"""Declarative base and shared column helpers."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Dialect, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON, TypeDecorator

# JSONB on PostgreSQL, plain JSON elsewhere so the test suite can also run
# against SQLite without changing the models.
JSONColumn = JSON().with_variant(JSONB(), "postgresql")


class EnumString[E: StrEnum](TypeDecorator[E]):
    """Stores a `StrEnum` as a short string, and reads it back as the enum.

    The stored representation is a plain ``VARCHAR``, which keeps migrations
    simple and the data readable in `psql`, while the mapped attribute is
    always a real enum member rather than a bare string.
    """

    impl = String
    cache_ok = True

    def __init__(self, enum_class: type[E], length: int = 16) -> None:
        super().__init__(length=length)
        self.enum_class = enum_class

    def process_bind_param(self, value: E | str | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        return self.enum_class(value).value

    def process_result_value(self, value: str | None, dialect: Dialect) -> E | None:
        return None if value is None else self.enum_class(value)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    type_annotation_map = {  # noqa: RUF012
        dict[str, Any]: JSONColumn,
    }


def uuid_pk() -> Mapped[uuid.UUID]:
    """Primary key column using a database native UUID where available."""
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """Adds server managed ``created_at`` / ``updated_at`` columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
