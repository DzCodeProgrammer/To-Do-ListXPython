from __future__ import annotations

import math
import uuid
from calendar import monthrange
from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.cache.task_cache import TaskCache
from app.config import settings
from app.models.task import Priority
from app.repositories.task import TaskRepository
from app.schemas.task import (
    SortOrder,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskSortBy,
    TaskSummary,
    TaskUpdate,
)


class TaskService:
    def __init__(self, repository: TaskRepository, cache: TaskCache):
        self.repository = repository
        self.cache = cache

    async def get(self, task_id: uuid.UUID, user_id: uuid.UUID) -> TaskResponse:
        key = self.cache.detail_key(user_id, task_id)
        cached = await self.cache.get(key)
        if cached:
            return TaskResponse.model_validate(cached)
        task = await self.repository.get_owned(task_id, user_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        response = TaskResponse.model_validate(task)
        await self.cache.set(key, response.model_dump(mode="json"), settings.task_cache_ttl_seconds)
        return response

    async def list(
        self,
        user_id: uuid.UUID,
        page: int,
        page_size: int,
        is_completed: bool | None,
        priority: Priority | None,
        search: str | None,
        overdue: bool,
        sort_by: TaskSortBy,
        sort_order: SortOrder,
    ) -> TaskListResponse:
        params = {
            "page": page,
            "page_size": page_size,
            "is_completed": is_completed,
            "priority": priority.value if priority else None,
            "search": search,
            "overdue": overdue,
            "sort_by": sort_by.value,
            "sort_order": sort_order.value,
        }
        key = self.cache.list_key(user_id, params)
        cached = await self.cache.get(key)
        if cached:
            return TaskListResponse.model_validate(cached)
        tasks, total = await self.repository.list_owned(
            user_id, page, page_size, is_completed, priority, search,
            overdue, sort_by, sort_order,
        )
        response = TaskListResponse(
            items=[TaskResponse.model_validate(task) for task in tasks],
            total=total,
            page=page,
            page_size=page_size,
            pages=math.ceil(total / page_size) if total else 0,
        )
        await self.cache.set_list(user_id, key, response.model_dump(mode="json"))
        return response

    async def summary(self, user_id: uuid.UUID) -> TaskSummary:
        key = self.cache.list_key(user_id, {"view": "summary"})
        cached = await self.cache.get(key)
        if cached:
            return TaskSummary.model_validate(cached)
        response = TaskSummary.model_validate(await self.repository.summary_owned(user_id))
        await self.cache.set_list(user_id, key, response.model_dump(mode="json"))
        return response

    async def calendar(self, user_id: uuid.UUID, year: int, month: int) -> list[TaskResponse]:
        key = self.cache.list_key(user_id, {"view": "calendar", "year": year, "month": month})
        cached = await self.cache.get(key)
        if cached:
            return [TaskResponse.model_validate(task) for task in cached["items"]]
        start = datetime(year, month, 1, tzinfo=UTC)
        last_day = monthrange(year, month)[1]
        if month == 12:
            end = datetime(year + 1, 1, 1, tzinfo=UTC)
        else:
            end = datetime(year, month + 1, 1, tzinfo=UTC)
        tasks = await self.repository.calendar_owned(user_id, start, end)
        response = [TaskResponse.model_validate(task) for task in tasks]
        await self.cache.set_list(
            user_id,
            key,
            {"items": [task.model_dump(mode="json") for task in response], "days": last_day},
        )
        return response

    async def create(self, user_id: uuid.UUID, data: TaskCreate) -> TaskResponse:
        task = await self.repository.create(user_id, data.model_dump())
        await self.cache.invalidate(user_id)
        return TaskResponse.model_validate(task)

    async def update(
        self, task_id: uuid.UUID, user_id: uuid.UUID, data: TaskUpdate
    ) -> TaskResponse:
        task = await self.repository.get_owned(task_id, user_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        task = await self.repository.update(task, data.model_dump(exclude_unset=True))
        await self.cache.invalidate(user_id, task_id)
        return TaskResponse.model_validate(task)

    async def delete(self, task_id: uuid.UUID, user_id: uuid.UUID) -> None:
        task = await self.repository.get_owned(task_id, user_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        await self.repository.delete(task)
        await self.cache.invalidate(user_id, task_id)
