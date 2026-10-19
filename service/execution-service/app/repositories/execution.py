from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution import Execution


class ExecutionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_executions(
        self,
        workspace_id: UUID,
        page: int = 1,
        page_size: int = 10,
        status: str | None = None,
    ) -> tuple[list[Execution], int]:
        try:
            filters = [
                Execution.workspace_id == workspace_id
            ]

            if status is not None:
                filters.append(
                    Execution.status == status
                )

            count_statement = (
                select(func.count())
                .select_from(Execution)
                .where(*filters)
            )

            total = (
                await self.session.execute(
                    count_statement
                )
            ).scalar_one()

            statement = (
                select(Execution)
                .where(*filters)
                .order_by(
                    Execution.created_at.desc(),
                    Execution.id.desc(),
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            )

            result = await self.session.execute(
                statement
            )

            executions = list(
                result.scalars().all()
            )

            return executions, total

        except SQLAlchemyError as exc:
            await self.session.rollback()

            raise RuntimeError(
                "Failed to retrieve execution history"
            ) from exc
