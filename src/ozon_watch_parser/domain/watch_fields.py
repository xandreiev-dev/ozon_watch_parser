import re


WATCH_BRANDS = [
    ("apple", "Apple"),
    ("samsung", "Samsung"),
    ("huawei", "Huawei"),
    ("honor", "Honor"),
    ("garmin", "Garmin"),
    ("amazfit", "Amazfit"),
    ("xiaomi", "Xiaomi"),
    ("redmi", "Xiaomi"),
    ("google", "Google"),
    ("pixel", "Google"),
    ("oneplus", "OnePlus"),
    ("vivo", "vivo"),
]

COLOR_KEYWORDS = [
    "black", "white", "silver", "gold", "gray", "grey", "blue", "green", "red",
    "pink", "purple", "orange", "yellow", "beige", "brown", "titanium", "graphite",
    "midnight", "starlight", "slate", "cream", "ivory",
    "черный", "чёрный", "белый", "серебристый", "серый", "синий", "зеленый",
    "зелёный", "красный", "розовый", "фиолетовый", "оранжевый", "желтый",
    "жёлтый", "бежевый", "коричневый", "титан", "титановый", "графит",
]

APPLE_COLOR_PATTERNS = [
    ("natural titanium", "Natural Titanium"),
    ("black titanium", "Black Titanium"),
    ("rose gold", "Rose Gold"),
    ("starlight", "Starlight"),
    ("midnight", "Midnight"),
    ("silver", "Silver"),
    ("gold", "Gold"),
    ("pink", "Pink"),
    ("blue", "Blue"),
    ("green", "Green"),
    ("red", "Red"),
    ("graphite", "Graphite"),
    ("черный титан", "Black Titanium"),
    ("чёрный", "Black"),
    ("черный", "Black"),
    ("серебристый", "Silver"),
    ("серый", "Gray"),
    ("золотой", "Gold"),
    ("розовое золото", "Rose Gold"),
    ("розовый", "Pink"),
    ("синий", "Blue"),
    ("зеленый", "Green"),
    ("зелёный", "Green"),
]

WARRANTY_PATTERNS = [
    r"гарант\w*\s*(\d+\s*(?:мес|месяц|месяцев|год|года|лет))",
    r"гарантия\s*(\d+\s*(?:мес|месяц|месяцев|год|года|лет))",
    r"гарантия\s*до\s*([0-9\.]+)",
    r"\b1\s*год\b",
    r"\b12\s*мес\b",
]

MODEL_GARBAGE_PARTS = [
    r"\bmetal loop\b",
    r"\bbluetooth\b",
    r"\blte\b",
    r"\bwi[- ]?fi\b",
    r"\b\d{2}\s*mm\b",
    r"\b\d{2}\s*мм\b",
    r"\bleather band\b",
    r"\bsilicone band\b",
    r"\bновые\b",
    r"\bновый\b",
    r"\bновая\b",
    r"\bnew\b",
    r"\bоригинал\b",
    r"\bв наличии\b",
    r"\bдоставка\b",
]

VALID_APPLE_SERIES = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def cleanup_model_value(value: str) -> str:
    value = clean_text(value or "")
    for garbage in MODEL_GARBAGE_PARTS:
        value = re.sub(garbage, "", value, flags=re.IGNORECASE)
    for color in COLOR_KEYWORDS:
        value = re.sub(rf"\b{re.escape(color)}\b", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" -_,/")


def extract_brand(title: str, description: str = "", brand_hint: str = "") -> str:
    hint = (brand_hint or "").lower().strip()
    for key, brand in WATCH_BRANDS:
        if hint == key:
            return brand

    full = f"{title or ''} {description or ''}".lower()
    for key, brand in WATCH_BRANDS:
        if key in full:
            return brand
    return ""


def extract_condition(title: str, description: str = "") -> str:
    full = clean_text(f"{title or ''} {description or ''}").lower()
    used_patterns = [r"\bб/у\b", r"\bбу\b", r"\bused\b", r"\bуцен[а-я]*\b", r"\bношен[а-я]*\b"]
    new_patterns = [
        r"\bновые\b",
        r"\bновый\b",
        r"\bновая\b",
        r"\bnew\b",
        r"\bзапечатан[а-я]*\b",
        r"\bне активирован[а-я]*\b",
    ]
    if any(re.search(pattern, full, flags=re.IGNORECASE) for pattern in used_patterns):
        return "used"
    if any(re.search(pattern, full, flags=re.IGNORECASE) for pattern in new_patterns):
        return "new"
    return ""


def extract_size(title: str, description: str = "") -> str:
    full = clean_text(f"{title or ''} {description or ''}")
    for pattern in [r"\b(\d{2})\s*мм\b", r"\b(\d{2})mm\b"]:
        match = re.search(pattern, full, flags=re.IGNORECASE)
        if match:
            return f"{match.group(1)} мм"
    return ""


def extract_apple_color(title: str, description: str = "") -> str:
    full = clean_text(f"{title or ''} {description or ''}").lower()
    found = []
    for raw, normalized in APPLE_COLOR_PATTERNS:
        if re.search(rf"\b{re.escape(raw)}\b", full, flags=re.IGNORECASE) and normalized not in found:
            found.append(normalized)
    return ", ".join(found[:2])


def extract_color(title: str, description: str = "") -> str:
    lower = clean_text(f"{title or ''} {description or ''}").lower()
    if "apple watch" in lower or re.search(r"\bs(?:2|3|4|5|6|7|8|9|10|11)\b", lower):
        return extract_apple_color(title, description)

    found = []
    for color in COLOR_KEYWORDS:
        if re.search(rf"\b{re.escape(color)}\b", lower, flags=re.IGNORECASE) and color not in found:
            found.append(color)
    return ", ".join(found[:2])


def extract_warranty(title: str, description: str = "") -> str:
    full = clean_text(f"{title or ''} {description or ''}".lower())
    for pattern in WARRANTY_PATTERNS:
        match = re.search(pattern, full, flags=re.IGNORECASE)
        if match:
            return match.group(1) if match.groups() else match.group(0)
    return ""


def is_target_watch_product(title: str, description: str = "") -> bool:
    full = clean_text(f"{title or ''} {description or ''}").lower()
    if not full:
        return False

    accessory_patterns = [
        r"^\s*(чехол|ремешок|стекло|пленк|заряд|кабель)",
        r"\b(чехол|ремешок|стекло|пленк)\s+(для|на)\b",
        r"\b(case|strap|screen protector|charger|cable)\s+(for|для)\b",
    ]
    band_patterns = [
        r"\bsmart\s*band\b",
        r"\bmi\s*band\b",
        r"\bфитнес[-\s]*браслет\b",
        r"\bgalaxy\s*fit\s*\d*\b",
        r"\bhuawei\s*band\b",
        r"\bhonor\s*band\b",
        r"\bxiaomi\s*band\b",
    ]
    if any(re.search(pattern, full, flags=re.IGNORECASE) for pattern in accessory_patterns):
        return False
    if any(re.search(pattern, full, flags=re.IGNORECASE) for pattern in band_patterns):
        return False

    return bool(re.search(r"\bwatch\b|час[ыо]|смарт[-\s]*час|smart\s*watch", full, flags=re.IGNORECASE))


def _model_from_head(title: str, brand_aliases: list[str], line_patterns: list[str]) -> str:
    head = clean_text((title or "").split(",", 1)[0])
    lower = head.lower()
    lower = re.sub(r"\b(смарт[-\s]*часы|умные\s+часы|smart\s+watch|наручные\s+смарт\s+часы)\b", " ", lower)
    for alias in brand_aliases:
        lower = re.sub(rf"\b{re.escape(alias)}\b", " ", lower, flags=re.IGNORECASE)
    lower = clean_text(lower)
    for pattern in line_patterns:
        match = re.search(pattern, lower, flags=re.IGNORECASE)
        if match:
            return cleanup_model_value(match.group(1))
    return ""


def extract_garmin_model(title: str, description: str = "") -> str:
    lower = clean_text(f"{title or ''} {description or ''}").lower()
    patterns = [
        r"(garmin fenix\s*[0-9a-zx\-\+ ]*)",
        r"(garmin forerunner\s*[0-9a-zx\-\+ ]*)",
        r"(garmin venu\s*[0-9a-zx\-\+ ]*)",
        r"(garmin epix\s*[0-9a-zx\-\+ ]*)",
        r"(garmin instinct\s*[0-9a-zx\-\+ ]*)",
        r"(garmin lily\s*[0-9a-zx\-\+ ]*)",
        r"(garmin tactix\s*[0-9a-zx\-\+ ]*)",
        r"(garmin marq\s*[0-9a-zx\-\+ ]*)",
        r"(garmin vivomove\s*[0-9a-zx\-\+ ]*)",
        r"(garmin vivoactive\s*[0-9a-zx\-\+ ]*)",
        r"(garmin approach\s*[0-9a-zx\-\+ ]*)",
        r"(garmin enduro\s*[0-9a-zx\-\+ ]*)",
        r"(garmin quatix\s*[0-9a-zx\-\+ ]*)",
        r"(garmin descent\s*[0-9a-zx\-\+ ]*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower, flags=re.IGNORECASE)
        if match:
            value = cleanup_model_value(match.group(1)).title()
            return value.replace("Garmin", "Garmin").replace("Marq", "MARQ")
    return ""


def extract_amazfit_model(title: str, description: str = "") -> str:
    return _model_from_head(
        f"{title or ''} {description or ''}",
        ["amazfit"],
        [
            r"((?:t[-\s]?rex|bip|active|balance|gts|gtr|cheetah|falcon|zepp)[a-z0-9®\-\s]*)",
            r"(a\d{4}\s+[a-z0-9\-\s]+)",
        ],
    )


def extract_huawei_model(title: str, description: str = "") -> str:
    return _model_from_head(
        f"{title or ''} {description or ''}",
        ["huawei"],
        [
            r"((?:watch\s*)?(?:gt|fit|d|ultimate|buds|kids|gt runner)[a-z0-9\-\s]*)",
            r"(watch\s+[a-z0-9\-\s]+)",
        ],
    )


def extract_honor_model(title: str, description: str = "") -> str:
    return _model_from_head(
        f"{title or ''} {description or ''}",
        ["honor"],
        [
            r"((?:choice\s+)?watch[a-z0-9\-\s]*)",
            r"(watch\s*\d[a-z0-9\-\s]*)",
        ],
    )


def extract_samsung_model(title: str, description: str = "") -> str:
    return _model_from_head(
        f"{title or ''} {description or ''}",
        ["samsung"],
        [
            r"(galaxy\s+watch\s+ultra[a-z0-9\-\s]*)",
            r"(galaxy\s+watch\s*\d*[a-z0-9\-\s]*)",
            r"(watch\s*\d+[a-z0-9\-\s]*)",
        ],
    )


def extract_xiaomi_model(title: str, description: str = "") -> str:
    return _model_from_head(
        f"{title or ''} {description or ''}",
        ["xiaomi", "redmi"],
        [
            r"((?:redmi\s+)?watch\s*[a-z0-9\-\s]*)",
            r"(s\d+\s*[a-z0-9\-\s]*)",
        ],
    )


def extract_google_model(title: str, description: str = "") -> str:
    return _model_from_head(
        f"{title or ''} {description or ''}",
        ["google"],
        [
            r"(pixel\s+watch\s*\d*[a-z0-9\-\s]*)",
            r"(watch\s*\d+[a-z0-9\-\s]*)",
        ],
    )


def extract_oneplus_model(title: str, description: str = "") -> str:
    return _model_from_head(
        f"{title or ''} {description or ''}",
        ["oneplus"],
        [r"(watch\s*\d*[a-z0-9\-\s]*)"],
    )


def extract_vivo_model(title: str, description: str = "") -> str:
    return _model_from_head(
        f"{title or ''} {description or ''}",
        ["vivo"],
        [r"(watch\s*[a-z0-9\-\s]*)"],
    )


def extract_apple_model(title: str, description: str = "") -> str:
    lower = clean_text(f"{title or ''} {description or ''}").lower()
    series_group = "|".join(VALID_APPLE_SERIES)

    se_short_match = re.search(r"\bapple\b.*\bse\s*(2|3|2022|2024|2025)?\b", lower, flags=re.IGNORECASE)
    if se_short_match and "watch" not in lower:
        raw_version = se_short_match.group(1) or ""
        if raw_version in {"2", "2022", "2024"}:
            return "Apple Watch SE 2"
        if raw_version in {"3", "2025"}:
            return "Apple Watch SE 3"
        return "Apple Watch SE"

    watch_s_match = re.search(r"\bwatch\s*s\s*(2|3|4|5|6|7|8|9|10|11)\b", lower, flags=re.IGNORECASE)
    if watch_s_match:
        return f"Apple Watch Series {watch_s_match.group(1)}"

    watchs_match = re.search(r"\bwatchs(2|3|4|5|6|7|8|9|10|11)\b", lower, flags=re.IGNORECASE)
    if watchs_match:
        return f"Apple Watch Series {watchs_match.group(1)}"

    series_ultra_match = re.search(r"\bwatch\s+series\s+ultra\s*(2|3)?\b", lower, flags=re.IGNORECASE)
    if series_ultra_match:
        suffix = series_ultra_match.group(1) or ""
        return clean_text(f"Apple Watch Ultra {suffix}")

    ultra_match = re.search(r"\bwatch\s+ultra\s*(2|3)?\b", lower, flags=re.IGNORECASE)
    if ultra_match:
        suffix = ultra_match.group(1) or ""
        return clean_text(f"Apple Watch Ultra {suffix}")

    se_match = re.search(
        r"\bwatch\s+(?:series\s+)?se\s*(?:gen\s*)?(2|3|2022|2024|2025)?\b",
        lower,
        flags=re.IGNORECASE,
    )
    if se_match:
        raw_version = se_match.group(1) or ""
        if raw_version in {"2", "2022", "2024"}:
            return "Apple Watch SE 2"
        if raw_version in {"3", "2025"}:
            return "Apple Watch SE 3"
        return "Apple Watch SE"

    series_match = re.search(
        rf"\bwatch\s+series\s*({series_group})\b",
        lower,
        flags=re.IGNORECASE,
    )
    if series_match:
        return f"Apple Watch Series {series_match.group(1)}"

    compact_series_match = re.search(
        rf"\bwatch\s+series({series_group})\b",
        lower,
        flags=re.IGNORECASE,
    )
    if compact_series_match:
        return f"Apple Watch Series {compact_series_match.group(1)}"

    patterns = [
        rf"(apple watch ultra\s*(?:2|3)?)\b",
        rf"(apple watch se(?:\s*(?:2|3|gen\s*2|gen\s*3|2022|2024))?)\b",
        rf"(apple watch series\s*(?:{series_group}))\b",
        rf"(apple watch\s*(?:series\s*)?(?:{series_group}))\b",
        rf"\b(s(?:{series_group}))\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower, flags=re.IGNORECASE)
        if not match:
            continue
        value = clean_text(match.group(1))
        se2 = re.search(r"apple watch se\s*(gen\s*2|2022|2)", value.lower())
        if se2:
            return "Apple Watch SE 2"
        se3 = re.search(r"apple watch se\s*(gen\s*3|2024|3)", value.lower())
        if se3:
            return "Apple Watch SE 3"
        short_series = re.fullmatch(r"s(2|3|4|5|6|7|8|9|10|11)", value.lower())
        if short_series:
            return f"Apple Watch Series {short_series.group(1)}"
        direct_series = re.fullmatch(r"apple watch\s*(2|3|4|5|6|7|8|9|10|11)", value.lower())
        if direct_series:
            return f"Apple Watch Series {direct_series.group(1)}"
        value = cleanup_model_value(value)
        value = re.sub(r"\bapple\b", "Apple", value, flags=re.IGNORECASE)
        value = re.sub(r"\bwatch\b", "Watch", value, flags=re.IGNORECASE)
        value = re.sub(r"\bseries\b", "Series", value, flags=re.IGNORECASE)
        value = re.sub(r"\bse\b", "SE", value, flags=re.IGNORECASE)
        value = re.sub(r"\bultra\b", "Ultra", value, flags=re.IGNORECASE)
        return value
    return ""


def extract_model(title: str, description: str = "") -> str:
    brand = extract_brand(title, description)
    if brand == "Apple":
        return extract_apple_model(title, description)
    if brand == "Garmin":
        return extract_garmin_model(title, description) or _model_from_head(
            f"{title or ''} {description or ''}",
            ["garmin"],
            [
                r"((?:fenix|forerunner|venu|epix|instinct|lily|tactix|marq|vivomove|vivoactive|approach|enduro|quatix|descent)[a-z0-9®\-\+\s]*)"
            ],
        )
    if brand == "Amazfit":
        return extract_amazfit_model(title, description)
    if brand == "Huawei":
        return extract_huawei_model(title, description)
    if brand == "Honor":
        return extract_honor_model(title, description)
    if brand == "Samsung":
        return extract_samsung_model(title, description)
    if brand == "Xiaomi":
        return extract_xiaomi_model(title, description)
    if brand == "Google":
        return extract_google_model(title, description)
    if brand == "OnePlus":
        return extract_oneplus_model(title, description)
    if brand == "vivo":
        return extract_vivo_model(title, description)

    lower = clean_text(f"{title or ''} {description or ''}").lower()
    patterns = [
        r"(samsung galaxy watch\s*\d+(?: classic)?(?: pro)?)",
        r"(huawei watch(?: gt)?(?: fit)?(?: d)?(?: ultimate)?\s*[a-z0-9\- ]*)",
        r"(honor watch\s*[a-z0-9\- ]*)",
        r"(amazfit [a-z0-9\- ]+)",
        r"((?:xiaomi|redmi) watch[a-z0-9\- ]*)",
        r"(google pixel watch\s*\d*)",
        r"(oneplus watch\s*\d*)",
        r"(vivo watch\s*[a-z0-9\- ]*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower, flags=re.IGNORECASE)
        if match:
            return cleanup_model_value(match.group(1))
    return ""
