import math
import re
from functools import lru_cache

import requests


CBR_DAILY_JSON_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
DUTY_FREE_THRESHOLD_EUR = 200
CUSTOMS_DUTY_RATE = 0.15
OZON_CUSTOMS_CHARGE_RUB = 689
DEFAULT_EUR_RATE = 100.0


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
    "глобал",
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


@lru_cache(maxsize=1)
def get_eur_rate(timeout: int = 8) -> float:
    try:
        response = requests.get(
            CBR_DAILY_JSON_URL,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        eur = (response.json().get("Valute", {}) or {}).get("EUR", {}) or {}
        value = eur.get("Value") or eur.get("Previous")
        nominal = eur.get("Nominal") or 1
        if value:
            return float(value) / float(nominal)
    except Exception:
        pass
    return DEFAULT_EUR_RATE


def is_global_text(text: str) -> str:
    lower = (text or "").lower()
    if any(marker in lower for marker in LOCAL_MARKERS):
        return "Нет"
    if any(marker in lower for marker in GLOBAL_MARKERS):
        return "Да"
    return "Нет"


def calc_ozon_like_duty(price_rub: int | float, eur_rate: float | None = None) -> int | None:
    threshold_rub = DUTY_FREE_THRESHOLD_EUR * (eur_rate or get_eur_rate())
    over = float(price_rub) - threshold_rub
    if over <= 0:
        return None
    duty = over * CUSTOMS_DUTY_RATE
    return int(math.ceil(duty + OZON_CUSTOMS_CHARGE_RUB))


def estimate_ozon_like_duty(
    price_rub: int | float | None,
    text: str,
    delivery_days: int | None,
    full_price: int | float | None = None,
    discount_price: int | float | None = None,
    eur_rate: float | None = None,
) -> int | None:
    lower = (text or "").lower()
    if any(marker in lower for marker in LOCAL_MARKERS):
        return None

    if delivery_days is None or delivery_days < 5:
        return None

    prices = [
        coerce_price(value)
        for value in (price_rub, full_price, discount_price)
    ]
    prices = [value for value in prices if value is not None]
    if not prices:
        return None

    full = coerce_price(full_price) or max(prices)
    discount = coerce_price(discount_price) or coerce_price(price_rub) or full
    if full and discount and full > discount * 3:
        full = discount

    discount_ratio = 0.0
    if full:
        discount_ratio = max(0.0, min(1.0, (full - discount) / full))

    has_global_marker = any(marker in lower for marker in GLOBAL_MARKERS)

    if delivery_days <= 10 and discount_ratio <= 0.10:
        return None

    if discount_ratio == 0 and delivery_days >= 7:
        return calc_ozon_like_duty(discount, eur_rate=eur_rate)

    duty_signals = 0
    if has_global_marker:
        duty_signals += 1
    if delivery_days >= 7:
        duty_signals += 1
    if discount_ratio > 0.10:
        duty_signals += 1

    if duty_signals >= 2:
        return calc_ozon_like_duty(discount, eur_rate=eur_rate)
    return None


def coerce_price(value) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    if not value:
        return None
    digits = re.sub(r"\D+", "", str(value))
    return int(digits) if digits else None
