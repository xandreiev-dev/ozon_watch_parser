import math
import re


LOCAL_MARKERS = (
    "ростест",
    "eac",
    "еас",
    "российская версия",
    "для россии",
    "официальная гарантия",
)

GLOBAL_MARKERS = (
    "global",
    "usa",
    "us version",
    "eu",
    "европейская версия",
    "china",
    "cn",
    "hong kong",
    "korean",
    "japan",
    "jp",
    "для других стран",
)


def is_global_text(text: str) -> str:
    lower = (text or "").lower()
    if any(marker in lower for marker in LOCAL_MARKERS):
        return "Нет"
    if any(marker in lower for marker in GLOBAL_MARKERS):
        return "Да"
    return "Нет"


def estimate_ozon_like_duty(price_rub: int | float | None, text: str, delivery_days: int | None) -> int | None:
    if not price_rub:
        return None
    lower = (text or "").lower()
    if any(marker in lower for marker in LOCAL_MARKERS):
        return None
    has_global_marker = any(marker in lower for marker in GLOBAL_MARKERS)
    slow_delivery = delivery_days is not None and delivery_days >= 8
    if not has_global_marker and not slow_delivery:
        return None

    eur_rate = 100
    threshold_rub = 200 * eur_rate
    over = float(price_rub) - threshold_rub
    if over <= 0:
        return None
    duty = over * 0.15
    service_fee = 500
    return int(math.ceil(duty + service_fee))


def coerce_price(value) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    if not value:
        return None
    digits = re.sub(r"\D+", "", str(value))
    return int(digits) if digits else None
