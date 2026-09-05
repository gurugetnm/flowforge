"""Authentication request and response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel

MIN_PASSWORD_LENGTH = 10


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=200)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Name cannot be blank.")
        return stripped

    @field_validator("password")
    @classmethod
    def _reject_trivial_passwords(cls, value: str) -> str:
        if value.strip() != value:
            raise ValueError("Password cannot start or end with whitespace.")
        if len(set(value)) < 5:
            raise ValueError("Password is too repetitive.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class UserResponse(ORMModel):
    id: uuid.UUID
    email: str
    name: str
    created_at: datetime
