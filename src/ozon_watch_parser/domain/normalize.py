from __future__ import annotations

from datetime import date

from ozon_watch_parser.config.brands import BRAND_DISPLAY_NAMES
from ozon_watch_parser.ozon.models import ListingItem
from ozon_watch_parser.utils.dates import parse_ozon_delivery_date
from ozon_watch_parser.utils.tax import coerce_price, estimate_ozon_like_duty, is_global_text
from ozon_watch_parser.utils.url import article_from_url

from .watch_fields import (
    extract_brand,
    extract_color,
    extract_condition,
    extract_model,
    extract_size,
    extract_warranty,
)


def normalize_listing_item(
    item: ListingItem,
    brand_hint: str = "",
    condition_hint: str = "",
) -> dict:
    title = item.title or ""
    description = ""
    article = article_from_url(item.url)
    parsed_delivery = parse_ozon_delivery_date(item.delivery_date)
    delivery_days = (parsed_delivery - date.today()).days if parsed_delivery else None
    price = coerce_price(item.price)
    discount_price = coerce_price(item.discount_price)
    if price and discount_price and price > discount_price * 3:
        price = discount_price
    source_text = " ".join([title, item.url])

    brand = extract_brand(title, description, brand_hint=brand_hint)
    if not brand and brand_hint:
        brand = BRAND_DISPLAY_NAMES.get(brand_hint, brand_hint.title())

    tax_price = estimate_ozon_like_duty(discount_price or price, source_text, delivery_days)

    return {
        "Название": title,
        "Цена": discount_price or price,
        "URL": item.url,
        "Описание": description,
        "Дата публикации": "",
        "Продавец": item.seller_name,
        "Адрес": "",
        "Адрес пользователя": "",
        "Координаты": "",
        "Изображения": item.image_url,
        "Поднято": "",
        "Звезды": item.shop_rating,
        "Отзывы": item.reviews_count,
        "Доставка": item.delivery_date,
        "brand": brand,
        "model": extract_model(title, description),
        "condition": extract_condition(title, description) or condition_hint,
        "size": extract_size(title, description),
        "color": extract_color(title, description),
        "warranty": extract_warranty(title, description),
        "product_url": item.url,
        "shop_rating": item.shop_rating,
        "reviews_count": item.reviews_count,
        "delivery_date": item.delivery_date,
        "delivery_days": delivery_days,
        "Article": article,
        "is_global": is_global_text(source_text),
        "tax_price": tax_price,
        "title / product name": title,
        "Price": price,
        "Discount Price": discount_price,
        "source_brand": brand_hint,
    }
