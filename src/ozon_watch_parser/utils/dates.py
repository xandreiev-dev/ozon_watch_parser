from __future__ import annotations

from datetime import date, datetime, timedelta


MONTHS_RU = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}


def parse_ozon_delivery_date(value: str, today: date | None = None) -> date | None:
    if not value:
        return None
    today = today or date.today()
    raw = value.strip().lower()
    if raw in {"сегодня", "today"}:
        return today
    if raw in {"завтра", "tomorrow"}:
        return today + timedelta(days=1)
    parts = raw.split()
    if len(parts) != 2:
        return None
    try:
        day = int(parts[0])
    except ValueError:
        return None
    month = MONTHS_RU.get(parts[1])
    if not month:
        return None
    candidate = date(today.year, month, day)
    if candidate < today - timedelta(days=30):
        candidate = date(today.year + 1, month, day)
    return candidate


def next_run_at(hour: int = 8, minute: int = 0) -> datetime:
    now = datetime.now()
    run_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if run_at <= now:
        run_at += timedelta(days=1)
    return run_at
