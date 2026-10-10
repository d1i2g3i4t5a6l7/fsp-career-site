import asyncio
import heapq
import itertools
import time
from contextlib import asynccontextmanager


class ChannelLimiter:
    """Ограничивает число одновременных запросов к одному каналу модели.

    Запросы сверх лимита ждут в очереди: сначала по приоритету (меньше — раньше),
    внутри приоритета — по порядку прихода. После 429 канал ставится на паузу целиком,
    чтобы ожидающие запросы не добивали исчерпанный лимит повторно.

    Лимит действует в пределах одного процесса — все вызовы моделей идут через один шлюз.
    """

    def __init__(self, name: str, max_concurrency: int):
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        self.name = name
        self.max_concurrency = max_concurrency
        self._active = 0
        self._queue: list[tuple[int, int, asyncio.Future[None]]] = []
        self._seq = itertools.count()
        self._paused_until = 0.0

    @property
    def active(self) -> int:
        return self._active

    @property
    def waiting(self) -> int:
        return sum(1 for _, _, fut in self._queue if not fut.done())

    def pause(self, seconds: float) -> None:
        self._paused_until = max(self._paused_until, time.monotonic() + seconds)

    async def acquire(self, priority: int) -> None:
        if self._active < self.max_concurrency and self.waiting == 0:
            self._active += 1
        else:
            fut: asyncio.Future[None] = asyncio.get_running_loop().create_future()
            heapq.heappush(self._queue, (priority, next(self._seq), fut))
            try:
                await fut
            except asyncio.CancelledError:
                # Слот уже успели передать нам — отдаём его следующему.
                # Если не успели, отменённый future останется в очереди, release() его пропустит.
                if fut.done() and not fut.cancelled():
                    self.release()
                raise

        delay = self._paused_until - time.monotonic()
        if delay > 0:
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                self.release()
                raise

    def release(self) -> None:
        while self._queue:
            _, _, fut = heapq.heappop(self._queue)
            if not fut.done():
                # Слот переходит к ожидающему напрямую, счётчик активных не меняется.
                fut.set_result(None)
                return
        self._active -= 1

    @asynccontextmanager
    async def slot(self, priority: int):
        await self.acquire(priority)
        try:
            yield
        finally:
            self.release()
