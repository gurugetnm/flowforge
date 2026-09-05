"""Schema building blocks shared by several resources."""

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    """Response model populated directly from an ORM instance."""

    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    """A slice of a larger collection."""

    items: list[T]
    total: int = Field(ge=0, description="Total number of matching records.")
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total
