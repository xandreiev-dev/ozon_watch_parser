AVITO_BASE_COLUMNS = [
    "Название",
    "Цена",
    "URL",
    "Описание",
    "Дата публикации",
    "Продавец",
    "Адрес",
    "Адрес пользователя",
    "Координаты",
    "Изображения",
    "Поднято",
    "Звезды",
    "Отзывы",
    "Доставка",
]

WATCH_COLUMNS = [
    "brand",
    "model",
    "condition",
    "size",
    "color",
    "warranty",
]

OZON_COLUMNS = [
    "product_url",
    "shop_rating",
    "reviews_count",
    "delivery_date",
    "delivery_days",
    "Article",
    "is_global",
    "tax_price",
    "title / product name",
    "Price",
    "Discount Price",
    "source_brand",
]

OUTPUT_COLUMNS = AVITO_BASE_COLUMNS + WATCH_COLUMNS + OZON_COLUMNS
