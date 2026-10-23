import asyncio
import os
from uuid import UUID

from app.services.execution_queue import (
    execute_pending_execution,
    inspect_recoverable_executions,
)


EXECUTION_MAX_CONCURRENCY = int(
    os.getenv("EXECUTION_MAX_CONCURRENCY", "5")
)

DISPATCH_INTERVAL_SECONDS = 2


class ExecutionDispatcher:
    def __init__(self):
        if EXECUTION_MAX_CONCURRENCY < 1:
            raise ValueError(
                "EXECUTION_MAX_CONCURRENCY must be positive"
            )

        self.semaphore = asyncio.Semaphore(
            EXECUTION_MAX_CONCURRENCY
        )

        self.active_tasks: set[asyncio.Task] = set()
        self.active_ids: set[UUID] = set()

        self.wakeup_event = asyncio.Event()
        self.running = False

    async def _execute(self, execution_id: UUID):
        try:
            await execute_pending_execution(execution_id)

        finally:
            self.active_ids.discard(execution_id)
            self.semaphore.release()

    def _on_task_done(self, task: asyncio.Task):
        self.active_tasks.discard(task)

        if not task.cancelled():
            # Retrieve exceptions to avoid unhandled task warnings.
            task.exception()

        # A slot is now available.
        self.wakeup_event.set()

    async def dispatch_pending(self):
        """Dispatch pending executions up to the concurrency limit."""

        available_slots = (
            EXECUTION_MAX_CONCURRENCY
            - len(self.active_tasks)
        )

        if available_slots <= 0:
            return

        recovery = await inspect_recoverable_executions(
            limit=min(available_slots, 100)
        )

        for item in recovery["pending"]:
            execution_id = UUID(item["execution_id"])

            if execution_id in self.active_ids:
                continue

            await self.semaphore.acquire()

            self.active_ids.add(execution_id)

            try:
                task = asyncio.create_task(
                    self._execute(execution_id)
                )

                self.active_tasks.add(task)
                task.add_done_callback(
                    self._on_task_done
                )

            except BaseException:
                self.active_ids.discard(execution_id)
                self.semaphore.release()
                raise

    async def run(self):
        """Dispatch work periodically or when an execution finishes."""

        self.running = True

        try:
            while self.running:
                self.wakeup_event.clear()

                await self.dispatch_pending()

                if not self.running:
                    break

                try:
                    await asyncio.wait_for(
                        self.wakeup_event.wait(),
                        timeout=DISPATCH_INTERVAL_SECONDS,
                    )
                except asyncio.TimeoutError:
                    pass

        except asyncio.CancelledError:
            raise

        finally:
            self.running = False

    async def shutdown(self):
        """Stop dispatching and wait for active executions."""

        self.running = False
        self.wakeup_event.set()

        if self.active_tasks:
            await asyncio.gather(
                *list(self.active_tasks),
                return_exceptions=True,
            )
