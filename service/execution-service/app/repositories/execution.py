from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import aliased
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.models.dead_letter_event import DeadLetterEvent
from app.models.execution import Execution
from app.models.execution_step import ExecutionStep
from app.engine.status import ExecutionStatus

from app.models.human_approval import HumanApproval
from app.engine.approval_status import HumanApprovalStatus
from app.engine.step_status import ExecutionStepStatus

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

    
 
    async def request_cancellation(
        self,
        execution_id: UUID,
        workspace_id: UUID,
    ) -> str | None:
        """
        Cancel pending or waiting executions immediately.
        Request cooperative cancellation for running executions.
        """

        # Lock the execution first so cancellation and
        # approval decisions cannot change it simultaneously.
        result = await self.session.execute(
            select(Execution)
            .where(
                Execution.id == execution_id,
                Execution.workspace_id == workspace_id,
            )
            .with_for_update()
        )

        execution = result.scalar_one_or_none()

        if execution is None:
            return None

        if execution.status == ExecutionStatus.CANCELLED:
            return "already_cancelled"

        if execution.status in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
        }:
            return "not_cancellable"

        # Running workflows stop cooperatively.
        # Do not terminate an external action in progress.
        if execution.status == ExecutionStatus.RUNNING:
            if execution.cancel_requested_at is None:
                execution.cancel_requested_at = (
                    datetime.now(timezone.utc)
                )

            return "cancellation_requested"

        # Pending workflows have not started.
        if execution.status == ExecutionStatus.PENDING:
            execution.status = ExecutionStatus.CANCELLED
            execution.cancel_requested_at = (
                datetime.now(timezone.utc)
            )
            execution.completed_at = datetime.now(timezone.utc)

            execution.claimed_by = None
            execution.heartbeat_at = None
            execution.lease_expires_at = None

            return "cancelled"

        # Cancel executions waiting for human approval.
        if execution.status == ExecutionStatus.WAITING_FOR_APPROVAL:
            now = datetime.now(timezone.utc)

            execution.status = ExecutionStatus.CANCELLED
            execution.cancel_requested_at = now
            execution.completed_at = now

            execution.claimed_by = None
            execution.heartbeat_at = None
            execution.lease_expires_at = None

            # Invalidate pending human approvals.
            await self.session.execute(
                update(HumanApproval)
                .where(
                    HumanApproval.execution_id == execution_id,
                    HumanApproval.workspace_id == workspace_id,
                    HumanApproval.status == HumanApprovalStatus.PENDING,
                )
                .values(
                    status=HumanApprovalStatus.CANCELLED,
                )
            )

            # Mark waiting approval steps as cancelled.
            await self.session.execute(
                update(ExecutionStep)
                .where(
                    ExecutionStep.execution_id == execution_id,
                    ExecutionStep.status
                    == ExecutionStepStatus.WAITING_FOR_APPROVAL,
                )
                .values(
                    status=ExecutionStepStatus.CANCELLED,
                    completed_at=func.now(),
                )
            )

            return "cancelled"

        return "not_cancellable"



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


    def replay_tree(self, workspace_id: UUID):
        """Map every attempt to its original run, including replays of replays.

        Both sides of every traversal are scoped to the current workspace. A
        missing/inaccessible parent is treated as a root, never traversed.
        UNION (rather than UNION ALL) also bounds traversal on malformed cycles.
        """
        parent = aliased(Execution)
        has_parent = select(parent.id).where(
            parent.id == Execution.replay_of_execution_id,
            parent.workspace_id == workspace_id,
        ).exists()
        tree = select(
            Execution.id.label("execution_id"),
            Execution.id.label("root_id"),
        ).where(
            Execution.workspace_id == workspace_id,
            ~has_parent,
        ).cte("replay_tree", recursive=True)
        return tree.union(select(Execution.id, tree.c.root_id).join(
            tree, Execution.replay_of_execution_id == tree.c.execution_id,
        ).where(Execution.workspace_id == workspace_id))

    async def list_execution_groups(self, workspace_id, page=1, page_size=10, status=None):
        try:
            tree = self.replay_tree(workspace_id)
            ranked = select(
                Execution.id.label("execution_id"), tree.c.root_id,
                func.count().over(partition_by=tree.c.root_id).label("attempt_count"),
                func.row_number().over(
                    partition_by=tree.c.root_id,
                    order_by=(Execution.created_at.desc(), Execution.id.desc()),
                ).label("position"),
            ).join(tree, Execution.id == tree.c.execution_id).where(
                Execution.workspace_id == workspace_id,
            ).subquery()
            filters = [ranked.c.position == 1, Execution.workspace_id == workspace_id]
            if status is not None:
                # A recovered group belongs in Completed, not Failed.
                filters.append(Execution.status == status)
            base = select(Execution).join(ranked, Execution.id == ranked.c.execution_id).where(*filters)
            total = (await self.session.execute(
                select(func.count()).select_from(base.subquery())
            )).scalar_one()
            statement = base.add_columns(ranked.c.root_id, ranked.c.attempt_count).order_by(
                Execution.created_at.desc(), Execution.id.desc(),
            ).offset((page - 1) * page_size).limit(page_size)
            return (await self.session.execute(statement)).all(), total
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise RuntimeError("Failed to retrieve execution groups") from exc

    async def list_execution_attempts(self, workspace_id, execution_id, page=1, page_size=10):
        try:
            tree = self.replay_tree(workspace_id)
            root_id = (await self.session.execute(select(tree.c.root_id).where(
                tree.c.execution_id == execution_id,
            ))).scalar_one_or_none()
            if root_id is None:
                return None
            base = select(Execution).join(tree, Execution.id == tree.c.execution_id).where(
                tree.c.root_id == root_id, Execution.workspace_id == workspace_id,
            )
            total = (await self.session.execute(
                select(func.count()).select_from(base.subquery())
            )).scalar_one()
            statement = base.order_by(Execution.created_at.asc(), Execution.id.asc()).offset(
                (page - 1) * page_size
            ).limit(page_size)
            return list((await self.session.execute(statement)).scalars().all()), total, root_id
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise RuntimeError("Failed to retrieve execution attempts") from exc

    async def get_execution_lineage(self, workspace_id, execution_id):
        """Identify the original run and the selected attempt's position."""
        try:
            tree = self.replay_tree(workspace_id)
            root_id = select(tree.c.root_id).where(
                tree.c.execution_id == execution_id,
            ).scalar_subquery()
            ranked = select(
                Execution.id.label("id"),
                tree.c.root_id.label("execution_group_id"),
                func.count().over().label("attempt_count"),
                func.row_number().over(
                    order_by=(Execution.created_at.asc(), Execution.id.asc()),
                ).label("attempt_number"),
            ).join(tree, Execution.id == tree.c.execution_id).where(
                tree.c.root_id == root_id, Execution.workspace_id == workspace_id,
            ).subquery()
            result = await self.session.execute(select(ranked).where(ranked.c.id == execution_id))
            row = result.mappings().one_or_none()
            return {key: row[key] for key in ("execution_group_id", "attempt_count", "attempt_number")} if row else {}
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise RuntimeError("Failed to retrieve execution lineage") from exc

    async def get_recovery_events(self, workspace_id, execution_ids):
        if not execution_ids:
            return {}
        result = await self.session.execute(
            select(DeadLetterEvent.execution_id, DeadLetterEvent.id, DeadLetterEvent.status).where(
                DeadLetterEvent.workspace_id == workspace_id,
                DeadLetterEvent.execution_id.in_(execution_ids),
            )
        )
        return {row.execution_id: {"dead_letter_event_id": row.id, "recovery_status": row.status} for row in result}
