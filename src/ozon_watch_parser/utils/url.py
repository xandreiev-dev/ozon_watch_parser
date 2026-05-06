import re
from urllib.parse import parse_qsl, urlencode, urlparse


def normalize_ozon_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    if parsed.netloc.lower() in {"ozon.kz", "www.ozon.kz"}:
        parsed = parsed._replace(scheme="https", netloc="www.ozon.ru")
    elif parsed.netloc.lower() == "ozon.ru":
        parsed = parsed._replace(scheme="https", netloc="www.ozon.ru")
    return parsed.geturl()


def build_page_url(base_url: str, page_num: int) -> str:
    parsed = urlparse(base_url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params["page"] = str(page_num)
    return parsed._replace(query=urlencode(params)).geturl()


def article_from_url(url: str) -> str:
    if not url:
        return ""
    match = re.search(r"-(\d+)(?:/)?$", url.split("?")[0])
    if match:
        return match.group(1)
    match = re.search(r"/product/[^/]*?(\d+)(?:/)?$", url.split("?")[0])
    return match.group(1) if match else ""


def listing_url_variants(base_url: str) -> list[str]:
    variants = [base_url]
    parsed = urlparse(base_url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))

    if params.get("sorting") != "price":
        by_price = dict(params)
        by_price["sorting"] = "price"
        variants.append(parsed._replace(query=urlencode(by_price)).geturl())

    if params.get("sorting") != "rating":
        by_rating = dict(params)
        by_rating["sorting"] = "rating"
        variants.append(parsed._replace(query=urlencode(by_rating)).geturl())

    seen = set()
    unique = []
    for url in variants:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique
