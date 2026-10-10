"""Зачисление платёжных событий. Провайдер может прислать одно событие несколько раз."""


def process(events: list[dict]) -> int:
    """Сумма зачислений; каждое событие учитывается один раз."""
    seen = set()
    total = 0
    for event in events:
        if event["id"] in seen:
            continue
        seen.add(event["id"])
        total += event["amount"]
    return total
