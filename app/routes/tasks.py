import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.cache.rate_limit import RateLimiter
from app.cache.redis import get_redis
from app.config import settings
from app.dependencies import CurrentUser, TaskServiceDep
from app.models.task import Priority
from app.schemas.task import (
    SortOrder,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskSortBy,
    TaskSummary,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def user_rate_limit(request: Request, user: CurrentUser) -> None:
    await RateLimiter(get_redis()).check(
        str(user.id), "api", settings.rate_limit_requests, settings.rate_limit_window_seconds
    )


RateLimitedUser = Annotated[
    object, Depends(user_rate_limit),
]


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    user: CurrentUser,
    service: TaskServiceDep,
    _: RateLimitedUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    is_completed: bool | None = None,
    priority: Priority | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    overdue: bool = False,
    sort_by: TaskSortBy = TaskSortBy.created_at,
    sort_order: SortOrder = SortOrder.desc,
):
    return await service.list(
        user.id, page, page_size, is_completed, priority, search,
        overdue, sort_by, sort_order,
    )


@router.get("/summary", response_model=TaskSummary)
async def task_summary(user: CurrentUser, service: TaskServiceDep, _: RateLimitedUser):
    return await service.summary(user.id)


@router.get("/calendar", response_model=list[TaskResponse])
async def task_calendar(
    user: CurrentUser,
    service: TaskServiceDep,
    _: RateLimitedUser,
    year: Annotated[int, Query(ge=2000, le=2100)],
    month: Annotated[int, Query(ge=1, le=12)],
):
    return await service.calendar(user.id, year, month)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID, user: CurrentUser, service: TaskServiceDep, _: RateLimitedUser
):
    return await service.get(task_id, user.id)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate, user: CurrentUser, service: TaskServiceDep, _: RateLimitedUser
):
    return await service.create(user.id, data)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID, data: TaskUpdate, user: CurrentUser, service: TaskServiceDep,
    _: RateLimitedUser,
):
    return await service.update(task_id, user.id, data)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID, user: CurrentUser, service: TaskServiceDep, _: RateLimitedUser,
) -> Response:
    await service.delete(task_id, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
