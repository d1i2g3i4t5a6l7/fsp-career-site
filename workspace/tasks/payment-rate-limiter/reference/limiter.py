"""Ограничитель запросов партнёров к платёжному API."""
import time
from collections import deque


class RateLimiter:
    """Не больше limit запросов за последние window секунд на один ключ партнёра."""

    def __init__(self, limit: int = 100, window: float = 60.0, clock=time.monotonic):
        self.limit = limit
        self.window = window
        self.clock = clock  # источник текущего времени
        self._hits: dict[str, deque[float]] = {}  # ключ партнёра → время пропущенных запросов в окне

    def allow(self, key: str) -> bool:
        """True — пропустить запрос, False — отказать (партнёр получит 429)."""
        now = self.clock()
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False  # отказ не записываем: повторы партнёра не должны продлевать блокировку
        hits.append(now)
        return True
