import uuid
from datetime import UTC, datetime

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Priority, Task
from app.schemas.task import SortOrder, TaskSortBy


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_owned(self, task_id: uuid.UUID, user_id: uuid.UUID) -> Task | None:
        result = await self.session.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        return result.scalar_one_or_none()

    def _filtered_query(
        self,
        user_id: uuid.UUID,
        is_completed: bool | None,
        priority: Priority | None,
        search: str | None,
        overdue: bool,
    ):
        query = select(Task).where(Task.user_id == user_id)
        if is_completed is not None:
            query = query.where(Task.is_completed == is_completed)
        if priority is not None:
            query = query.where(Task.priority == priority)
        if search:
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            query = query.where(
                or_(
                    Task.title.ilike(pattern, escape="\\"),
                    Task.description.ilike(pattern, escape="\\"),
                )
            )
        if overdue:
            query = query.where(
                Task.is_completed.is_(False),
                Task.due_date.is_not(None),
                Task.due_date < datetime.now(UTC),
            )
        return query

    async def list_owned(
        self,
        user_id: uuid.UUID,
        page: int,
        page_size: int,
        is_completed: bool | None = None,
        priority: Priority | None = None,
        search: str | None = None,
        overdue: bool = False,
        sort_by: TaskSortBy = TaskSortBy.created_at,
        sort_order: SortOrder = SortOrder.desc,
    ) -> tuple[list[Task], int]:
        query = self._filtered_query(user_id, is_completed, priority, search, overdue)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        sort_columns = {
            TaskSortBy.created_at: Task.created_at,
            TaskSortBy.due_date: Task.due_date,
            TaskSortBy.priority: case(
                (Task.priority == Priority.low, 1),
                (Task.priority == Priority.medium, 2),
                (Task.priority == Priority.high, 3),
            ),
        }
        sort_column = sort_columns[sort_by]
        ordering = sort_column.asc() if sort_order == SortOrder.asc else sort_column.desc()
        result = await self.session.execute(
            query.order_by(ordering.nulls_last(), Task.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), int(total or 0)

    async def summary_owned(self, user_id: uuid.UUID) -> dict[str, int]:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(
                func.count(Task.id).label("total"),
                func.count(Task.id).filter(Task.is_completed.is_(True)).label("completed"),
                func.count(Task.id).filter(Task.is_completed.is_(False)).label("pending"),
                func.count(Task.id)
                .filter(
                    Task.is_completed.is_(False),
                    Task.due_date.is_not(None),
                    Task.due_date < now,
                )
                .label("overdue"),
                func.count(Task.id)
                .filter(Task.is_completed.is_(False), Task.priority == Priority.high)
                .label("high_priority"),
            ).where(Task.user_id == user_id)
        )
        row = result.one()
        return {field: int(getattr(row, field) or 0) for field in row._fields}

    async def calendar_owned(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> list[Task]:
        result = await self.session.execute(
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.due_date >= start,
                Task.due_date < end,
            )
            .order_by(Task.due_date.asc(), Task.created_at.asc())
        )
        return list(result.scalars().all())

    async def create(self, user_id: uuid.UUID, data: dict) -> Task:
        task = Task(user_id=user_id, **data)
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def update(self, task: Task, data: dict) -> Task:
        for field, value in data.items():
            setattr(task, field, value)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def delete(self, task: Task) -> None:
        await self.session.delete(task)
        await self.session.commit()
