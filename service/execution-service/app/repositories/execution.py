from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution import Execution
from app.models.execution_step import ExecutionStep


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


    
    async def get_execution_by_id(
        self,
        execution_id: UUID,
        workspace_id: UUID,
    ) -> Execution | None:
        try:
            statement = (
                select(Execution)
                .where(
                    Execution.id == execution_id,
                    Execution.workspace_id == workspace_id,
                )
            )

            result = await self.session.execute(statement)

            return result.scalar_one_or_none()

        except SQLAlchemyError as exc:
            await self.session.rollback()

            raise RuntimeError(
                "Failed to retrieve execution details"
            ) from exc


    async def list_execution_steps(
        self,
        execution_id: UUID,
        workspace_id: UUID,
    ) -> list[ExecutionStep] | None:
        try:
            statement = (
                select(ExecutionStep)
                .join(
                    Execution,
                    ExecutionStep.execution_id == Execution.id,
                )
                .where(
                    Execution.id == execution_id,
                    Execution.workspace_id == workspace_id,
                )
                .order_by(
                    ExecutionStep.sequence.asc(),
                    ExecutionStep.created_at.asc(),
                    ExecutionStep.id.asc(),
                )
            )

            result = await self.session.execute(
                statement
            )

            steps = list(result.scalars().all())

            # Distinguish an unknown execution
            # from a valid execution with no steps.
            if not steps:
                execution = await self.get_execution_by_id(
                    execution_id=execution_id,
                    workspace_id=workspace_id,
                )

                if execution is None:
                    return None

            return steps

        except SQLAlchemyError as exc:
            await self.session.rollback()

            raise RuntimeError(
                "Failed to retrieve execution steps"
            ) from exc
