from dataclasses import dataclass


@dataclass(slots=True)
class ListingItem:
    url: str
    title: str = ""
    price: int | None = None
    discount_price: int | None = None
    shop_rating: float | None = None
    reviews_count: int | None = None
    delivery_date: str = ""
    seller_name: str = ""
    image_url: str = ""

    @classmethod
    def from_raw(cls, raw: dict) -> "ListingItem":
        return cls(
            url=str(raw.get("url") or ""),
            title=str(raw.get("title") or ""),
            price=raw.get("price"),
            discount_price=raw.get("discount_price"),
            shop_rating=raw.get("shop_rating"),
            reviews_count=raw.get("reviews_count"),
            delivery_date=str(raw.get("delivery_date") or ""),
            seller_name=str(raw.get("seller_name") or ""),
            image_url=str(raw.get("image_url") or ""),
        )
