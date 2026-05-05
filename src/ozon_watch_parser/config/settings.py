from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

from ozon_watch_parser.config.brands import BRAND_URLS


@dataclass(slots=True)
class AppConfig:
    pages: int = 20
    min_cards: int = 200
    export_dir: str = "brand_exports"
    cdp_url: str = "http://localhost:9222"
    auto_launch_chrome: bool = True
    headless: bool = False
    urls_by_brand: dict[str, list[str]] | None = None


def _as_url_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _normalize_url_map(raw: dict[str, Any]) -> dict[str, list[str]]:
    urls_by_brand = {brand: [] for brand in BRAND_URLS}
    for brand, value in raw.items():
        urls_by_brand[str(brand).strip().lower()] = _as_url_list(value)
    return urls_by_brand


def load_app_config(path: str | Path = "config.toml") -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        return AppConfig(urls_by_brand={brand: [] for brand in BRAND_URLS})

    with config_path.open("rb") as file:
        raw = tomllib.load(file)

    parser = raw.get("parser", {})
    cdp = raw.get("cdp", {})
    urls = raw.get("urls", {})

    return AppConfig(
        pages=int(parser.get("pages", 20)),
        min_cards=int(parser.get("min_cards", 200)),
        export_dir=str(parser.get("export_dir", "brand_exports")),
        cdp_url=str(cdp.get("url", "http://localhost:9222")),
        auto_launch_chrome=bool(cdp.get("auto_launch_chrome", True)),
        headless=bool(cdp.get("headless", False)),
        urls_by_brand=_normalize_url_map(urls),
    )
