from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from ozon_watch_parser.browser import BrowserSettings
from ozon_watch_parser.config import BRAND_URLS, load_app_config
from ozon_watch_parser.services import OzonWatchParser


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def async_main() -> None:
    parser = argparse.ArgumentParser(description="Ozon smart watch parser")
    parser.add_argument("--config", default="config.toml", help="Путь к TOML-конфигу со ссылками")
    parser.add_argument("--url", default=None, help="Явный URL листинга для одного запуска")
    parser.add_argument("--brand", choices=sorted(BRAND_URLS.keys()), default=None, help="Парсить только один бренд")
    parser.add_argument("--pages", type=int, default=None)
    parser.add_argument("--min-cards", type=int, default=None)
    parser.add_argument("--export-dir", default=None)
    parser.add_argument("--cdp", dest="use_cdp", action="store_true", default=True)
    parser.add_argument("--no-cdp", dest="use_cdp", action="store_false")
    parser.add_argument("--cdp-url", default=None)
    parser.add_argument("--headless", action="store_true", default=None)
    parser.add_argument("--no-auto-launch-chrome", dest="auto_launch_chrome", action="store_false", default=None)
    parser.add_argument("--once", action="store_true", help="Запустить один раз и выйти")
    args = parser.parse_args()

    app_config = load_app_config(args.config)
    browser_settings = BrowserSettings(
        use_cdp=args.use_cdp,
        cdp_url=args.cdp_url or app_config.cdp_url,
        headless=app_config.headless if args.headless is None else args.headless,
        auto_launch_chrome=app_config.auto_launch_chrome if args.auto_launch_chrome is None else args.auto_launch_chrome,
    )
    ozon_parser = OzonWatchParser(
        browser_settings=browser_settings,
        export_dir=args.export_dir or app_config.export_dir,
    )
    brands = [args.brand] if args.brand else None
    pages = args.pages if args.pages is not None else app_config.pages
    min_cards = args.min_cards if args.min_cards is not None else app_config.min_cards
    use_brand_min_cards = args.min_cards is None
    urls_by_brand = app_config.urls_by_brand or {}

    if args.once:
        out_path, rows = await ozon_parser.run_once(
            urls_by_brand=urls_by_brand,
            brands=brands,
            pages=pages,
            min_cards=min_cards,
            url_override=args.url,
            use_brand_min_cards=use_brand_min_cards,
        )
        if out_path:
            logging.info("Общий файл сформирован: %s (%s строк)", out_path, rows)
        else:
            logging.warning("Общий файл не сформирован")
        return

    await ozon_parser.run_daily(
        urls_by_brand=urls_by_brand,
        brands=brands,
        pages=pages,
        min_cards=min_cards,
        url_override=args.url,
        use_brand_min_cards=use_brand_min_cards,
    )


def main() -> None:
    configure_logging()
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
