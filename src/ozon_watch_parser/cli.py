from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from ozon_watch_parser.browser import BrowserSettings
from ozon_watch_parser.config import BRAND_URLS
from ozon_watch_parser.services import OzonWatchParser


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def async_main() -> None:
    parser = argparse.ArgumentParser(description="Ozon smart watch parser")
    parser.add_argument("--url", default=None, help="Явный URL листинга для одного запуска")
    parser.add_argument("--brand", choices=sorted(BRAND_URLS.keys()), default=None, help="Парсить только один бренд")
    parser.add_argument("--pages", type=int, default=20)
    parser.add_argument("--min-cards", type=int, default=200)
    parser.add_argument("--export-dir", default="brand_exports")
    parser.add_argument("--cdp", dest="use_cdp", action="store_true", default=True)
    parser.add_argument("--no-cdp", dest="use_cdp", action="store_false")
    parser.add_argument("--cdp-url", default="http://localhost:9222")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--no-auto-launch-chrome", dest="auto_launch_chrome", action="store_false", default=True)
    parser.add_argument("--once", action="store_true", help="Запустить один раз и выйти")
    args = parser.parse_args()

    browser_settings = BrowserSettings(
        use_cdp=args.use_cdp,
        cdp_url=args.cdp_url,
        headless=args.headless,
        auto_launch_chrome=args.auto_launch_chrome,
    )
    ozon_parser = OzonWatchParser(browser_settings=browser_settings, export_dir=args.export_dir)
    brands = [args.brand] if args.brand else None

    if args.once:
        out_path, rows = await ozon_parser.run_once(
            brands=brands,
            pages=args.pages,
            min_cards=args.min_cards,
            url_override=args.url,
        )
        if out_path:
            logging.info("Общий файл сформирован: %s (%s строк)", out_path, rows)
        else:
            logging.warning("Общий файл не сформирован")
        return

    await ozon_parser.run_daily(
        brands=brands,
        pages=args.pages,
        min_cards=args.min_cards,
        url_override=args.url,
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
