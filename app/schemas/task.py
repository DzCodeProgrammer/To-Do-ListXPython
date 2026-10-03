import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.task import Priority


class TaskSortBy(StrEnum):
    created_at = "created_at"
    due_date = "due_date"
    priority = "priority"


class SortOrder(StrEnum):
    asc = "asc"
    desc = "desc"


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    is_completed: bool = False
    priority: Priority = Priority.medium
    due_date: datetime | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    is_completed: bool | None = None
    priority: Priority | None = None
    due_date: datetime | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("title must not be blank")
        return value

    @model_validator(mode="after")
    def title_must_not_be_null(self):
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("title must not be null")
        return self


class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int
    pages: int


class TaskSummary(BaseModel):
    total: int
    completed: int
    pending: int
    overdue: int
    high_priority: int
