from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright


logger = logging.getLogger(__name__)

MOSCOW_GEOLOCATION = {
    "latitude": 55.7558,
    "longitude": 37.6173,
}

OZON_GEOLOCATION_ORIGIN = "https://www.ozon.ru"
MOSCOW_LOCATION_QUERY = "141-99-90"


# Минимальный stealth-скрипт нужен для fallback-режима без CDP.
STEALTH_INIT_SCRIPT = r"""
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru', 'en'] });
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
window.chrome = window.chrome || { runtime: {}, app: {}, csi: function(){}, loadTimes: function(){} };
const origQuery = navigator.permissions ? navigator.permissions.query.bind(navigator.permissions) : null;
if (origQuery) {
  navigator.permissions.query = (p) =>
    p.name === 'notifications'
      ? Promise.resolve({ state: Notification.permission })
      : origQuery(p);
}
"""


@dataclass(slots=True)
class BrowserSettings:
    use_cdp: bool = True
    cdp_url: str = "http://localhost:9222"
    headless: bool = False
    auto_launch_chrome: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    locale: str = "ru-RU"
    timezone_id: str = "Europe/Moscow"


class BrowserManager:
    def __init__(self, settings: BrowserSettings):
        self.settings = settings
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.chrome_process: subprocess.Popen | None = None
        self._owns_browser = False
        self._moscow_location_applied = False

    @staticmethod
    def cdp_endpoint_ready(cdp_url: str) -> bool:
        try:
            with urllib.request.urlopen(f"{cdp_url}/json/version", timeout=2) as response:
                return response.status == 200
        except (urllib.error.URLError, TimeoutError, ValueError):
            return False

    async def wait_for_cdp(self, cdp_url: str, attempts: int = 15) -> bool:
        for attempt in range(1, attempts + 1):
            if self.cdp_endpoint_ready(cdp_url):
                return True
            logger.info("Жду CDP endpoint %s, попытка %s/%s", cdp_url, attempt, attempts)
            await asyncio.sleep(1)
        return False

    @staticmethod
    def chrome_executable() -> Path | None:
        candidates = [
            Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def launch_cdp_chrome(self) -> None:
        chrome = self.chrome_executable()
        if not chrome:
            raise RuntimeError("Chrome не найден в стандартных путях установки")
        # Отдельный профиль не смешивает парсерную сессию с обычным Chrome пользователя.
        profile_dir = Path(tempfile.gettempdir()) / "chrome-cdp-ozon-watch"
        profile_dir.mkdir(parents=True, exist_ok=True)
        port = urlparse(self.settings.cdp_url).port or 9222
        args = [
            str(chrome),
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--start-maximized",
        ]
        logger.info("Запускаю отдельный Chrome для CDP на порту %s", port)
        self.chrome_process = subprocess.Popen(args)
        self._owns_browser = True

    async def setup(self) -> Page:
        self.playwright = await async_playwright().start()
        if self.settings.use_cdp:
            await self._setup_cdp()
        else:
            await self._setup_owned_browser()

        if not self.page:
            raise RuntimeError("Не удалось создать страницу браузера")
        self.page.set_default_timeout(25000)
        self.page.set_default_navigation_timeout(45000)
        return self.page

    async def _setup_cdp(self) -> None:
        ready = self.cdp_endpoint_ready(self.settings.cdp_url)
        if not ready:
            if not self.settings.auto_launch_chrome:
                raise RuntimeError(
                    f"CDP endpoint {self.settings.cdp_url} недоступен. "
                    "Откройте Chrome с --remote-debugging-port=9222."
                )
            self.launch_cdp_chrome()
            ready = await self.wait_for_cdp(self.settings.cdp_url, attempts=30)
        if not ready:
            raise RuntimeError(f"Не удалось дождаться CDP endpoint {self.settings.cdp_url}")

        logger.info("Подключаюсь к Chrome через CDP: %s", self.settings.cdp_url)
        self.browser = await self.playwright.chromium.connect_over_cdp(self.settings.cdp_url)
        # В CDP-режиме стараемся использовать уже открытый контекст с живыми cookies Ozon.
        self.context = self.browser.contexts[0] if self.browser.contexts else await self.browser.new_context()
        await self.apply_moscow_geolocation()
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()

    async def _setup_owned_browser(self) -> None:
        self._owns_browser = True
        self.browser = await self.playwright.chromium.launch(
            headless=self.settings.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
                "--lang=ru-RU,ru",
            ],
            ignore_default_args=["--enable-automation"],
        )
        self.context = await self.browser.new_context(
            viewport={"width": self.settings.viewport_width, "height": self.settings.viewport_height},
            locale=self.settings.locale,
            timezone_id=self.settings.timezone_id,
            ignore_https_errors=True,
            extra_http_headers={
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )
        await self.context.add_init_script(STEALTH_INIT_SCRIPT)
        await self.apply_moscow_geolocation()
        self.page = await self.context.new_page()

    async def apply_moscow_geolocation(self) -> None:
        if not self.context:
            return
        try:
            await self.context.grant_permissions(
                ["geolocation"],
                origin=OZON_GEOLOCATION_ORIGIN,
            )
            await self.context.set_geolocation(MOSCOW_GEOLOCATION)
        except Exception as exc:
            logger.debug("Не удалось выставить geolocation Москвы: %s", exc)

    async def set_moscow_location_via_ui(self) -> None:
        if self._moscow_location_applied or not self.page:
            return

        await self.apply_moscow_geolocation()

        async def safe_click(locator, timeout: int = 3000) -> bool:
            try:
                await locator.first.click(force=True, timeout=timeout)
                return True
            except Exception:
                return False

        for _ in range(2):
            try:
                await self.page.keyboard.press("Escape")
            except Exception:
                pass
            await asyncio.sleep(0.35)

        # Регион выставляем именно через интерфейс Ozon, иначе цены и доставка могут быть не московскими.
        opener_candidates = (
            self.page.get_by_role(
                "button",
                name=re.compile(r"^(Краснодар|Москва|Укажите адрес|Пункт Ozon)", re.I),
            ),
            self.page.get_by_role(
                "button",
                name=re.compile(r"(Выбрать на карте|Добавить адрес|Укажите адрес|Пункт Ozon)", re.I),
            ),
        )

        opened = False
        for locator in opener_candidates:
            opened = await safe_click(locator)
            if opened:
                await asyncio.sleep(3)
                break

        for locator in (
            self.page.get_by_role(
                "button",
                name=re.compile(r"(Выбрать на карте|Выберите адрес доставки)", re.I),
            ),
            self.page.get_by_role(
                "button",
                name=re.compile(r"(Самовывоз|Пункт выдачи|Постамат)", re.I),
            ),
        ):
            if await safe_click(locator):
                opened = True
                await asyncio.sleep(2)

        if not opened:
            for _ in range(2):
                if await safe_click(opener_candidates[0]):
                    opened = True
                    await asyncio.sleep(1.7)
                    break

        if not opened:
            logger.warning("Не удалось открыть виджет выбора адреса Ozon")
            return

        search_input = None
        search_candidates = (
            self.page.locator('form.checkout_a7n div.sdk[label="Искать на карте"] textarea'),
            self.page.locator('div[data-widget="addressEditForm"] div.sdk[label="Искать на карте"] textarea'),
            self.page.locator('div.sdk[label="Искать на карте"] textarea'),
        )
        for _ in range(8):
            for candidate in search_candidates:
                try:
                    if await candidate.count():
                        search_input = candidate.first
                        break
                except Exception:
                    continue
            if search_input:
                break
            await asyncio.sleep(0.5)

        if search_input:
            for _ in range(2):
                try:
                    await search_input.click(timeout=5000)
                    await search_input.press("Control+A")
                    await search_input.press("Backspace")
                    await search_input.type(MOSCOW_LOCATION_QUERY, delay=50)
                    await asyncio.sleep(1.7)
                    break
                except Exception:
                    await asyncio.sleep(0.5)

        determine_button = self.page.get_by_role(
            "button",
            name=re.compile(r"Определить местоположение", re.I),
        )
        try:
            await determine_button.first.click(force=True, timeout=5000)
        except Exception:
            try:
                await self.page.keyboard.press("Enter")
            except Exception:
                pass
        await asyncio.sleep(1.5)

        pickup_button = self.page.get_by_role(
            "button",
            name=re.compile(r"Заберу отсюда", re.I),
        )
        for _ in range(8):
            try:
                if await pickup_button.count():
                    await pickup_button.first.click(force=True, timeout=5000)
                    await asyncio.sleep(1.2)
                    break
            except Exception:
                pass

            try:
                await determine_button.first.click(force=True, timeout=3000)
            except Exception:
                try:
                    await self.page.keyboard.press("Enter")
                except Exception:
                    pass
            await asyncio.sleep(1.2)

        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass
        await asyncio.sleep(0.8)
        self._moscow_location_applied = True
        logger.info("Регион Ozon выставлен через UI: Москва")

    async def close(self) -> None:
        try:
            if self.browser and self._owns_browser:
                await self.browser.close()
        finally:
            self.browser = None
            self.context = None
            self.page = None
            if self.playwright:
                await self.playwright.stop()
            self.playwright = None
            self._close_autostarted_chrome()

    def _close_autostarted_chrome(self) -> None:
        pid = self.chrome_process.pid if self.chrome_process else None
        if pid:
            try:
                # Закрываем только Chrome, который был запущен самим парсером.
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
            except Exception:
                pass
        self.chrome_process = None
