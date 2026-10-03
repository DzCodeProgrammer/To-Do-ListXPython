import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.models.task import Priority
from app.schemas.task import SortOrder, TaskCreate, TaskSortBy, TaskUpdate
from app.services.task import TaskService


def task_object(user_id, task_id=None):
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=task_id or uuid.uuid4(), user_id=user_id, title="Test", description=None,
        is_completed=False, priority=Priority.medium, due_date=None,
        created_at=now, updated_at=now,
    )


@pytest.mark.asyncio
async def test_detail_cache_hit_skips_database():
    user_id, task_id = uuid.uuid4(), uuid.uuid4()
    task = task_object(user_id, task_id)
    repository = SimpleNamespace(get_owned=AsyncMock())
    cache = SimpleNamespace(
        detail_key=lambda *_: "key",
        get=AsyncMock(return_value={
            "id": str(task.id), "user_id": str(task.user_id), "title": task.title,
            "description": None, "is_completed": False, "priority": "medium",
            "due_date": None, "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }),
    )
    result = await TaskService(repository, cache).get(task_id, user_id)
    assert result.id == task_id
    repository.get_owned.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_invalidates_user_list_cache():
    user_id = uuid.uuid4()
    task = task_object(user_id)
    repository = SimpleNamespace(create=AsyncMock(return_value=task))
    cache = SimpleNamespace(invalidate=AsyncMock())
    result = await TaskService(repository, cache).create(user_id, TaskCreate(title="Test"))
    assert result.user_id == user_id
    cache.invalidate.assert_awaited_once_with(user_id)


@pytest.mark.asyncio
async def test_detail_cache_miss_reads_owned_task_and_fills_cache():
    user_id, task_id = uuid.uuid4(), uuid.uuid4()
    task = task_object(user_id, task_id)
    repository = SimpleNamespace(get_owned=AsyncMock(return_value=task))
    cache = SimpleNamespace(
        detail_key=lambda *_: "detail-key", get=AsyncMock(return_value=None),
        set=AsyncMock(),
    )

    result = await TaskService(repository, cache).get(task_id, user_id)

    assert result.id == task_id
    repository.get_owned.assert_awaited_once_with(task_id, user_id)
    cache.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_other_users_task_is_hidden_as_not_found():
    user_id, task_id = uuid.uuid4(), uuid.uuid4()
    repository = SimpleNamespace(get_owned=AsyncMock(return_value=None))
    cache = SimpleNamespace(detail_key=lambda *_: "key", get=AsyncMock(return_value=None))

    with pytest.raises(HTTPException) as error:
        await TaskService(repository, cache).get(task_id, user_id)

    assert error.value.status_code == 404
    repository.get_owned.assert_awaited_once_with(task_id, user_id)


@pytest.mark.asyncio
async def test_update_invalidates_detail_and_list_cache():
    user_id, task_id = uuid.uuid4(), uuid.uuid4()
    task = task_object(user_id, task_id)
    repository = SimpleNamespace(
        get_owned=AsyncMock(return_value=task), update=AsyncMock(return_value=task)
    )
    cache = SimpleNamespace(invalidate=AsyncMock())

    await TaskService(repository, cache).update(
        task_id, user_id, TaskUpdate(is_completed=True)
    )

    repository.get_owned.assert_awaited_once_with(task_id, user_id)
    cache.invalidate.assert_awaited_once_with(user_id, task_id)


@pytest.mark.asyncio
async def test_list_filter_and_sort_are_part_of_repository_call_and_cache_key():
    user_id = uuid.uuid4()
    repository = SimpleNamespace(list_owned=AsyncMock(return_value=([], 0)))
    cache = SimpleNamespace(
        list_key=lambda owner, params: f"{owner}:{params}",
        get=AsyncMock(return_value=None), set_list=AsyncMock(),
    )

    await TaskService(repository, cache).list(
        user_id, 2, 10, False, Priority.high, "laporan", True,
        TaskSortBy.due_date, SortOrder.asc,
    )

    repository.list_owned.assert_awaited_once_with(
        user_id, 2, 10, False, Priority.high, "laporan", True,
        TaskSortBy.due_date, SortOrder.asc,
    )
    key_params = cache.get.await_args.args[0]
    assert "overdue': True" in key_params
    assert "sort_by': 'due_date'" in key_params


@pytest.mark.asyncio
async def test_summary_cache_miss_queries_only_current_user_and_is_cached():
    user_id = uuid.uuid4()
    summary = {
        "total": 5, "completed": 2, "pending": 3, "overdue": 1, "high_priority": 2,
    }
    repository = SimpleNamespace(summary_owned=AsyncMock(return_value=summary))
    cache = SimpleNamespace(
        list_key=lambda owner, params: f"summary:{owner}:{params['view']}",
        get=AsyncMock(return_value=None), set_list=AsyncMock(),
    )

    result = await TaskService(repository, cache).summary(user_id)

    assert result.completed == 2
    repository.summary_owned.assert_awaited_once_with(user_id)
    cache.set_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_summary_cache_hit_skips_database():
    user_id = uuid.uuid4()
    cached = {
        "total": 4, "completed": 4, "pending": 0, "overdue": 0, "high_priority": 0,
    }
    repository = SimpleNamespace(summary_owned=AsyncMock())
    cache = SimpleNamespace(
        list_key=lambda *_: "summary-key", get=AsyncMock(return_value=cached)
    )

    result = await TaskService(repository, cache).summary(user_id)

    assert result.total == 4
    repository.summary_owned.assert_not_awaited()


@pytest.mark.asyncio
async def test_calendar_queries_selected_month_for_current_user_and_caches_result():
    user_id = uuid.uuid4()
    task = task_object(user_id)
    task.due_date = datetime(2026, 10, 12, tzinfo=UTC)
    repository = SimpleNamespace(calendar_owned=AsyncMock(return_value=[task]))
    cache = SimpleNamespace(
        list_key=lambda owner, params: f"calendar:{owner}:{params['year']}:{params['month']}",
        get=AsyncMock(return_value=None), set_list=AsyncMock(),
    )

    result = await TaskService(repository, cache).calendar(user_id, 2026, 10)

    assert result[0].id == task.id
    call = repository.calendar_owned.await_args
    assert call.args[0] == user_id
    assert call.args[1] == datetime(2026, 10, 1, tzinfo=UTC)
    assert call.args[2] == datetime(2026, 11, 1, tzinfo=UTC)
    cache.set_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_calendar_cache_hit_skips_database():
    user_id = uuid.uuid4()
    task = task_object(user_id)
    task.due_date = datetime(2026, 12, 2, tzinfo=UTC)
    cached_task = {
        "id": str(task.id), "user_id": str(user_id), "title": task.title,
        "description": None, "is_completed": False, "priority": "medium",
        "due_date": task.due_date.isoformat(), "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }
    repository = SimpleNamespace(calendar_owned=AsyncMock())
    cache = SimpleNamespace(
        list_key=lambda *_: "calendar-key",
        get=AsyncMock(return_value={"items": [cached_task], "days": 31}),
    )

    result = await TaskService(repository, cache).calendar(user_id, 2026, 12)

    assert len(result) == 1
    repository.calendar_owned.assert_not_awaited()
