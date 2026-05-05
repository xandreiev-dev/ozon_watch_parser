from ozon_watch_parser.domain.normalize import normalize_listing_item
from ozon_watch_parser.ozon.models import ListingItem
from ozon_watch_parser.config.settings import load_app_config
from ozon_watch_parser.domain.watch_fields import extract_model
from ozon_watch_parser.utils.url import article_from_url, build_page_url


def test_article_from_ozon_url():
    assert article_from_url("https://www.ozon.ru/product/apple-watch-series-10-123456789/") == "123456789"


def test_build_page_url_replaces_page():
    url = build_page_url("https://www.ozon.ru/category/smart-chasy-15516/?sorting=price&page=2", 5)
    assert "page=5" in url
    assert "sorting=price" in url


def test_normalize_apple_watch_item():
    item = ListingItem(
        url="https://www.ozon.ru/product/apple-watch-series-10-123456789/",
        title="Apple Watch Series 10 46 мм, Black",
        price=59990,
        discount_price=54990,
        shop_rating=4.8,
        reviews_count=120,
        delivery_date="5 мая",
    )

    row = normalize_listing_item(item, brand_hint="apple", condition_hint="new")

    assert row["brand"] == "Apple"
    assert row["model"] == "Apple Watch Series 10"
    assert row["size"] == "46 мм"
    assert row["Article"] == "123456789"
    assert row["Цена"] == 54990
    assert row["condition"] == "new"


def test_load_default_config():
    config = load_app_config("missing-config.toml")

    assert config.urls_by_brand is not None
    assert "apple" in config.urls_by_brand
    assert config.urls_by_brand["apple"] == []


def test_extract_ozon_apple_model_formats():
    assert extract_model("Apple Смарт-часы Watch SE 2, 44mm, Ink Loop") == "Apple Watch SE 2"
    assert (
        extract_model("Apple Смарт-часы Watch Series 11 (2025) - ремешок S/M, 42mm")
        == "Apple Watch Series 11"
    )
    assert (
        extract_model("Apple Смарт-часы Watch Ultra 3, 49mm, Black Titanium Case")
        == "Apple Watch Ultra 3"
    )
