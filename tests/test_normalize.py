from ozon_watch_parser.domain.normalize import normalize_listing_item
from ozon_watch_parser.ozon.models import ListingItem
from ozon_watch_parser.config.settings import load_app_config
from ozon_watch_parser.domain.watch_fields import extract_model
from ozon_watch_parser.utils.tax import calc_ozon_like_duty, estimate_ozon_like_duty
from ozon_watch_parser.utils.url import article_from_url, build_page_url, listing_url_variants


def test_article_from_ozon_url():
    assert article_from_url("https://www.ozon.ru/product/apple-watch-series-10-123456789/") == "123456789"


def test_build_page_url_replaces_page():
    url = build_page_url("https://www.ozon.ru/category/smart-chasy-15516/?sorting=price&page=2", 5)
    assert "page=5" in url
    assert "sorting=price" in url


def test_listing_url_variants_uses_two_passes_by_default():
    variants = listing_url_variants("https://www.ozon.ru/category/smart-chasy-15516/?text=watch")

    assert len(variants) == 2
    assert "sorting=price" in variants[1]
    assert all("sorting=rating" not in variant for variant in variants)


def test_listing_url_variants_can_include_rating_pass():
    variants = listing_url_variants(
        "https://www.ozon.ru/category/smart-chasy-15516/?text=watch",
        include_rating=True,
    )

    assert len(variants) == 3
    assert any("sorting=rating" in variant for variant in variants)


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
    assert config.min_price == 1000
    assert config.max_price == 300000


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


def test_calc_ozon_like_duty_uses_200_eur_threshold_and_ozon_charge():
    assert calc_ozon_like_duty(30000, eur_rate=95) == 2339
    assert calc_ozon_like_duty(18000, eur_rate=95) is None


def test_estimate_ozon_like_duty_uses_delivery_discount_and_global_signals():
    tax_price = estimate_ozon_like_duty(
        30000,
        "Huawei Watch Global",
        delivery_days=12,
        full_price=35000,
        discount_price=30000,
        eur_rate=95,
    )

    assert tax_price == 2339
    assert (
        estimate_ozon_like_duty(
            30000,
            "Huawei Watch EAC",
            delivery_days=12,
            full_price=35000,
            discount_price=30000,
            eur_rate=95,
        )
        is None
    )
    assert (
        estimate_ozon_like_duty(
            30000,
            "Huawei Watch",
            delivery_days=4,
            full_price=35000,
            discount_price=30000,
            eur_rate=95,
        )
        is None
    )
