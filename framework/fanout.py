"""Small async orchestration helpers (fan-out + concurrency limits)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")
U = TypeVar("U")


async def gather_with_limit(awaitables: list[Awaitable[T]], concurrency: int) -> list[T]:
    """Run awaitables with an upper bound on in-flight tasks.

    Preserves input order.
    """
    if concurrency < 1:
        raise ValueError("concurrency must be >= 1")

    semaphore = asyncio.Semaphore(concurrency)
    results: list[T | None] = [None] * len(awaitables)

    async def _run_one(idx: int, aw: Awaitable[T]) -> None:
        async with semaphore:
            results[idx] = await aw

    await asyncio.gather(*[_run_one(i, aw) for i, aw in enumerate(awaitables)])
    return [r for r in results if r is not None]


async def map_with_limit(
    items: list[U],
    worker: Callable[[U], Awaitable[T]],
    concurrency: int,
    delay_s: float = 0.0,
) -> list[T]:
    """Run worker(item) across items with concurrency and optional delay.

    Preserves input order.
    """
    if concurrency < 1:
        raise ValueError("concurrency must be >= 1")

    semaphore = asyncio.Semaphore(concurrency)
    results: list[T | None] = [None] * len(items)

    async def _run_one(idx: int, item: U) -> None:
        async with semaphore:
            results[idx] = await worker(item)
            if delay_s:
                await asyncio.sleep(delay_s)

    await asyncio.gather(*[_run_one(i, item) for i, item in enumerate(items)])
    return [r for r in results if r is not None]
