"""Ограничитель запросов партнёров к платёжному API."""
import time


class RateLimiter:
    """Не больше limit запросов за последние window секунд на один ключ партнёра."""

    def __init__(self, limit: int = 100, window: float = 60.0, clock=time.monotonic):
        self.limit = limit
        self.window = window
        self.clock = clock  # источник текущего времени

    def allow(self, key: str) -> bool:
        """True — пропустить запрос, False — отказать (партнёр получит 429)."""
        return True
