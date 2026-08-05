"""Background-task scheduler scaffold.

T14 only provides the queue + enqueue + run_one primitives; the worker loop
and integration with the upload pipeline arrive in T17. Kept minimal but
typed per ``coding-style.md``.
"""

from collections import deque
from typing import Awaitable, Callable, Deque


class Scheduler:
    """Lightweight FIFO coroutine queue.

    ``enqueue`` stores a zero-arg coroutine factory; ``run_one`` drains one
    item and awaits it. T17 will add a long-running worker loop.
    """

    def __init__(self) -> None:
        self._queue: Deque[Callable[[], Awaitable[None]]] = deque()

    def enqueue(self, coro_factory: Callable[[], Awaitable[None]]) -> None:
        """Append a coroutine factory to the queue."""
        self._queue.append(coro_factory)

    async def run_one(self) -> None:
        """Drain one item from the queue and await it. No-op if empty."""
        if not self._queue:
            return
        factory = self._queue.popleft()
        await factory()


scheduler = Scheduler()

__all__ = ["Scheduler", "scheduler"]
