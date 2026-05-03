from __future__ import annotations

import asyncio
import random

from playwright.async_api import Page

from .models import ListingItem


EXTRACT_LISTING_JS = r"""
(brandHint = '') => {
  const cards = document.querySelectorAll('.tile-root');
  const out = [];
  const brandNeedle = (brandHint || '').trim().toLowerCase();
  const titleNeedle = /Watch|watch|часы|Смарт|смарт|Apple|Samsung|Galaxy|Huawei|HUAWEI|Honor|Garmin|Amazfit|Xiaomi|Redmi|Pixel|OnePlus/i;

  cards.forEach(card => {
    const link = card.querySelector("a[href*='/product/']");
    if (!link) return;

    let url = link.getAttribute('href') || '';
    if (url.startsWith('/')) url = 'https://www.ozon.ru' + url;
    url = url.split('?')[0];

    const txt = card.innerText || '';
    const lines = txt.split('\n').map(s => s.trim()).filter(Boolean);

    let title = '';
    for (const line of lines) {
      const lower = line.toLowerCase();
      const brandOk = !brandNeedle || lower.includes(brandNeedle);
      if (line.length > 8 && brandOk && titleNeedle.test(line) && !/^\d[\d\s]*\s*₽$/.test(line)) {
        title = line;
        break;
      }
    }
    if (!title) {
      const aria = link.getAttribute('aria-label') || link.getAttribute('title') || '';
      if (aria && titleNeedle.test(aria)) title = aria.trim();
    }

    const priceMatches = [...txt.matchAll(/([\d\s\u00a0]+)\s*₽/g)]
      .map(m => parseInt(m[1].replace(/[\s\u00a0]/g, ''), 10))
      .filter(n => !isNaN(n) && n > 100);
    const discount_price = priceMatches[0] ?? null;
    const price = priceMatches[1] ?? priceMatches[0] ?? null;

    let shop_rating = null;
    for (let i = 0; i < lines.length; i++) {
      if (/^\d[.,]\d$/.test(lines[i])) {
        const next = lines[i + 1] || '';
        if (!/₽/.test(next) && (/отзыв|рейтинг|Ozon|оценк/i.test(next) || /\d/.test(next))) {
          shop_rating = parseFloat(lines[i].replace(',', '.'));
          break;
        }
      }
    }

    let reviews_count = null;
    for (const line of lines) {
      const match = line.match(/(\d[\d\s]*)\s+отзыв/i);
      if (match) {
        reviews_count = parseInt(match[1].replace(/\s+/g, ''), 10);
        break;
      }
    }

    let delivery_date = '';
    for (let i = lines.length - 1; i >= 0; i--) {
      if (/^\d{1,2}\s+[А-Яа-яЁё]+$/.test(lines[i]) || /^(сегодня|завтра)$/i.test(lines[i])) {
        delivery_date = lines[i];
        break;
      }
    }

    const image = card.querySelector('img');
    const image_url = image ? (image.currentSrc || image.src || '') : '';

    out.push({ url, title, price, discount_price, shop_rating, reviews_count, delivery_date, image_url });
  });
  return out;
}
"""


class ListingExtractor:
    def __init__(self, page: Page):
        self.page = page

    async def human_delay(self, minimum: float = 0.4, maximum: float = 1.2) -> None:
        await asyncio.sleep(random.uniform(minimum, maximum))

    async def check_blocked(self) -> bool:
        title = await self.page.title()
        body_text = await self.page.evaluate("() => document.body ? document.body.innerText.slice(0, 500) : ''")
        if "Доступ ограничен" in title or "Доступ ограничен" in body_text:
            return True
        return "Подтвердите" in body_text and "робот" in body_text.lower()

    async def fetch_listing_page(self, url: str, brand_hint: str = "", on_new_items=None) -> list[ListingItem]:
        await self.page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await self.human_delay(3, 5)

        if await self.check_blocked():
            raise RuntimeError("Ozon показал антибот/ограничение доступа. Нужен открытый залогиненный Chrome через CDP.")

        try:
            await self.page.mouse.move(400, 300)
            await self.page.mouse.move(800, 500, steps=10)
        except Exception:
            pass

        async def extract_items(retries: int = 3) -> list[ListingItem]:
            last_error = None
            for attempt in range(1, retries + 1):
                try:
                    raw_items = await self.page.evaluate(EXTRACT_LISTING_JS, brand_hint)
                    return [ListingItem.from_raw(raw) for raw in raw_items if raw.get("url")]
                except Exception as exc:
                    last_error = exc
                    if attempt < retries and ("Execution context was destroyed" in str(exc) or "navigation" in str(exc)):
                        await self.human_delay(0.8, 1.5)
                        continue
                    raise
            raise last_error

        async def wait_for_settle(retries: int = 4) -> list[ListingItem]:
            last_items: list[ListingItem] = []
            last_count = -1
            for _ in range(retries):
                last_items = await extract_items()
                if len(last_items) == last_count:
                    return last_items
                last_count = len(last_items)
                await self.human_delay(0.6, 1.0)
            return last_items

        max_scrolls = 250
        no_growth_patience = 5
        seen_urls: set[str] = set()
        items: list[ListingItem] = []
        empty_growth_streak = 0

        for _ in range(max_scrolls):
            await self.page.mouse.wheel(0, 600)
            await self.human_delay(0.4, 0.9)
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.human_delay(0.8, 1.5)
            items = await wait_for_settle()

            current_urls = {item.url for item in items if item.url}
            new_urls = current_urls - seen_urls
            if new_urls and on_new_items:
                await on_new_items([item for item in items if item.url in new_urls])

            seen_urls |= current_urls
            if new_urls:
                empty_growth_streak = 0
            else:
                empty_growth_streak += 1
            if empty_growth_streak >= no_growth_patience:
                break

        return items or await extract_items()
