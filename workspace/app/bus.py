import asyncio
from collections import defaultdict
from typing import Any


class EventBus:
    """Рассылка событий попытки открытым WebSocket-соединениям. В пределах одного процесса."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)

    def subscribe(self, attempt_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)
        self._subscribers[attempt_id].add(queue)
        return queue

    def unsubscribe(self, attempt_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers[attempt_id].discard(queue)
        if not self._subscribers[attempt_id]:
            del self._subscribers[attempt_id]

    def publish(self, attempt_id: str, message: dict[str, Any]) -> None:
        for queue in list(self._subscribers.get(attempt_id, ())):
            if not queue.full():  # зависший клиент не должен тормозить остальных
                queue.put_nowait(message)
