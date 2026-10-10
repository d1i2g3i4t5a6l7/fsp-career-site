import asyncio

import pytest

from app.llm.balancer import ChannelLimiter


async def test_never_exceeds_concurrency():
    limiter = ChannelLimiter("t", 2)
    running = 0
    peak = 0

    async def job():
        nonlocal running, peak
        async with limiter.slot(0):
            running += 1
            peak = max(peak, running)
            await asyncio.sleep(0.01)
            running -= 1

    await asyncio.gather(*(job() for _ in range(10)))
    assert peak == 2
    assert limiter.active == 0
    assert limiter.waiting == 0


async def test_priority_order_then_fifo():
    limiter = ChannelLimiter("t", 1)
    order: list[str] = []
    await limiter.acquire(0)  # занимаем единственный слот

    async def job(name: str, priority: int):
        async with limiter.slot(priority):
            order.append(name)

    tasks = [
        asyncio.create_task(job("bg1", 2)),
        asyncio.create_task(job("grade", 1)),
        asyncio.create_task(job("bg2", 2)),
        asyncio.create_task(job("chat", 0)),
    ]
    await asyncio.sleep(0)
    limiter.release()
    await asyncio.gather(*tasks)
    assert order == ["chat", "grade", "bg1", "bg2"]


async def test_cancelled_waiter_does_not_leak_slot():
    limiter = ChannelLimiter("t", 1)
    await limiter.acquire(0)
    waiter = asyncio.create_task(limiter.acquire(0))
    await asyncio.sleep(0)
    waiter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter
    limiter.release()
    assert limiter.active == 0
    # слот свободен: следующий захват не ждёт
    await asyncio.wait_for(limiter.acquire(0), timeout=0.1)


async def test_pause_delays_next_request():
    limiter = ChannelLimiter("t", 1)
    limiter.pause(0.05)
    loop = asyncio.get_running_loop()
    started = loop.time()
    async with limiter.slot(0):
        pass
    assert loop.time() - started >= 0.04
