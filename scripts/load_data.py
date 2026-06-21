#!/usr/bin/env python3
"""Load query dataset into SQLite (Phase 1)."""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DATABASE_PATH
from src.database import bulk_insert_queries, get_row_count, init_db

DEFAULT_CSV = ROOT / "data" / "queries.csv"
MIN_QUERY_COUNT = 200_000
BATCH_SIZE = 5_000

PRODUCTS = (
    "iphone",
    "samsung galaxy",
    "macbook",
    "ipad",
    "airpods",
    "laptop",
    "wireless earbuds",
    "gaming monitor",
    "mechanical keyboard",
    "python tutorial",
    "java tutorial",
    "react hooks",
    "docker compose",
    "kubernetes pods",
    "aws lambda",
    "machine learning",
    "data science",
    "neural network",
    "typescript generics",
    "graphql api",
)

CATEGORY_PRODUCTS: dict[str, tuple[str, ...]] = {
    "Electronics": (
        "smart tv",
        "bluetooth speaker",
        "power bank",
        "dslr camera",
        "smartwatch",
        "tablet",
        "gaming console",
        "wifi router",
    ),
    "Clothing": (
        "cotton kurta",
        "denim jeans",
        "running shoes",
        "winter jacket",
        "saree",
        "formal shirt",
        "sports t-shirt",
        "leather belt",
    ),
    "Groceries": (
        "basmati rice",
        "olive oil",
        "organic honey",
        "green tea",
        "protein powder",
        "almond milk",
        "instant noodles",
        "dark chocolate",
    ),
    "Home appliances": (
        "air conditioner",
        "washing machine",
        "microwave oven",
        "vacuum cleaner",
        "water purifier",
        "ceiling fan",
        "induction cooktop",
        "room heater",
    ),
    "Beauty products": (
        "face serum",
        "sunscreen spf 50",
        "hair oil",
        "lipstick",
        "moisturizer",
        "perfume",
        "face wash",
        "beard trimmer",
    ),
    "Books": (
        "fiction novel",
        "ncert textbook",
        "self help book",
        "comic book",
        "cookbook",
        "history book",
        "poetry collection",
        "exam guide",
    ),
    "Furniture": (
        "office chair",
        "study table",
        "sofa set",
        "queen size bed",
        "bookshelf",
        "dining table",
        "wardrobe",
        "mattress",
    ),
    "Automobiles": (
        "electric scooter",
        "car insurance",
        "bike helmet",
        "car tyre",
        "engine oil",
        "car battery",
        "dash cam",
        "bike service",
    ),
    "Travel": (
        "flight tickets",
        "hotel booking",
        "train reservation",
        "bus tickets",
        "holiday package",
        "travel insurance",
        "cab booking",
        "homestay",
    ),
}

INDIAN_CRICKET = (
    "ipl 2025",
    "ipl live score",
    "csk vs mi",
    "rcb vs kkr",
    "india vs australia",
    "world cup 2025",
    "icc rankings",
    "cricket highlights",
    "ms dhoni",
    "virat kohli century",
    "wtc final",
    "t20 world cup",
)

INDIAN_FESTIVALS = (
    "diwali gifts",
    "diwali decoration",
    "holi colours",
    "navratri garba",
    "raksha bandhan gifts",
    "ganesh chaturthi",
    "onam sadhya",
    "pongal recipes",
    "eid special dishes",
    "christmas cake india",
    "republic day parade",
    "independence day speech",
)

INDIAN_EXAMS = (
    "jee main 2025",
    "jee advanced syllabus",
    "neet preparation",
    "upsc prelims",
    "gate cse",
    "cat mock test",
    "cbse board exam",
    "ssc cgl",
    "nda admit card",
    "clat application",
)

INDIAN_ENTERTAINMENT = (
    "bollywood new release",
    "srk movie",
    "pushpa 2",
    "rrr sequel",
    "tamil movie download",
    "telugu blockbuster",
    "netflix india",
    "hotstar subscription",
    "spotify premium india",
    "k-pop india tour",
)

INDIAN_TECH = (
    "jio recharge",
    "airtel 5g",
    "upi payment",
    "paytm wallet",
    "aadhaar update",
    "digilocker",
    "bhim app",
    "phonepe offers",
    "swiggy coupon",
    "zomato gold",
)

DEVICE_MODIFIERS = ("pro", "max", "ultra", "plus", "mini", "2024", "2025")
SHOPPING_MODIFIERS = (
    "price",
    "deals",
    "cheap",
    "online",
    "in india",
    "free delivery",
    "emi",
    "cashback",
)
ACCESSORY_MODIFIERS = ("charger", "case", "screen protector", "review", "unboxing", "warranty")
TECH_MODIFIERS = (
    "for beginners",
    "crash course",
    "example",
    "setup",
    "config",
    "install",
    "fix",
    "tutorial",
)
EXAM_SUFFIXES = (
    "syllabus",
    "preparation",
    "admit card",
    "mock test",
    "application",
    "result",
    "answer key",
)

SHOPPING_QUALIFIERS = ("buy", "best", "top", "cheap", "latest", "compare", "near me")
TECH_QUALIFIERS = ("how to", "what is", "why is", "when is", "where is", "fix", "install", "setup", "config", "example")

IPHONE_MODELS = (
    "13",
    "13 mini",
    "14",
    "14 plus",
    "14 pro",
    "14 pro max",
    "15",
    "15 plus",
    "15 pro",
    "15 pro max",
)
IPL_TEAMS = ("csk", "mi", "rcb", "kkr", "srh", "gt", "dc", "rr", "pbks", "lsg")

INDIAN_CITIES = (
    "mumbai",
    "delhi",
    "bangalore",
    "chennai",
    "hyderabad",
    "pune",
    "kolkata",
    "ahmedabad",
    "jaipur",
    "lucknow",
    "surat",
    "noida",
    "gurgaon",
    "kochi",
    "chandigarh",
    "indore",
    "nagpur",
    "bhopal",
    "patna",
    "visakhapatnam",
    "thane",
    "vadodara",
    "ghaziabad",
    "ludhiana",
    "agra",
    "nashik",
    "faridabad",
    "meerut",
    "rajkot",
    "varanasi",
    "srinagar",
    "amritsar",
    "ranchi",
    "coimbatore",
    "jodhpur",
    "madurai",
    "guwahati",
    "vijayawada",
    "dehradun",
    "mangalore",
)

CLOTHING_SIZES = ("s", "m", "l", "xl", "xxl", "28", "30", "32", "34", "36")
CLOTHING_COLORS = (
    "black",
    "white",
    "blue",
    "red",
    "green",
    "navy",
    "maroon",
    "grey",
    "beige",
    "olive",
)

GROCERY_SIZES = ("500g", "1kg", "2kg", "5kg", "1 litre", "2 litre", "5 litre")

AC_CAPACITIES = ("1 ton", "1.5 ton", "2 ton")

BIKE_CC = ("125cc", "150cc", "200cc", "350cc")

LAPTOP_BRANDS = (
    "dell xps",
    "hp pavilion",
    "lenovo thinkpad",
    "asus vivobook",
    "acer aspire",
    "msi gaming",
)

BEAUTY_CONCERNS = ("oily skin", "dry skin", "sensitive skin", "acne", "anti aging")

FURNITURE_ROOMS = ("bedroom", "living room", "office", "study room", "dining room")

MOVIE_LANGUAGES = ("hindi", "tamil", "telugu", "malayalam", "kannada", "bengali")

YEARS = ("2020", "2021", "2022", "2023", "2024", "2025", "2026")

STORAGE_SIZES = ("64gb", "128gb", "256gb", "512gb", "1tb")

PRICE_BANDS = (
    "under 10000",
    "under 20000",
    "under 30000",
    "under 50000",
    "under 100000",
)

SAMSUNG_MODELS = (
    "s24",
    "s24 ultra",
    "s23",
    "s23 ultra",
    "a54",
    "a34",
    "z fold 5",
    "z flip 5",
)

MACBOOK_VARIANTS = ("air m2", "air m3", "pro 14 inch", "pro 16 inch")

IPAD_VARIANTS = ("air", "pro 11 inch", "pro 13 inch", "mini")

TRAVEL_DESTINATIONS = (
    "goa",
    "manali",
    "kerala",
    "shimla",
    "jaipur",
    "udaipur",
    "ooty",
    "munnar",
    "darjeeling",
    "rishikesh",
    "andaman",
    "ladakh",
    "agra",
    "mysore",
    "coorg",
)

BOOK_FORMATS = ("paperback", "hardcover", "kindle edition", "audiobook")

CRICKET_VIEWING = (
    "highlights",
    "schedule",
    "points table",
    "score today",
    "ticket booking",
)

ELECTRONICS_PRODUCTS = (
    "iphone",
    "samsung galaxy",
    "macbook",
    "ipad",
    "airpods",
    "laptop",
    "wireless earbuds",
    "gaming monitor",
    "mechanical keyboard",
)
TECH_PRODUCTS = (
    "python tutorial",
    "java tutorial",
    "react hooks",
    "docker compose",
    "kubernetes pods",
    "aws lambda",
    "machine learning",
    "data science",
    "neural network",
    "typescript generics",
    "graphql api",
)

ALL_CATEGORY_PRODUCTS = tuple(
    product for products in CATEGORY_PRODUCTS.values() for product in products
)
ALL_CATEGORIES = tuple(CATEGORY_PRODUCTS.keys())
INDIAN_TERMS = (
    INDIAN_CRICKET + INDIAN_FESTIVALS + INDIAN_EXAMS + INDIAN_ENTERTAINMENT + INDIAN_TECH
)
ALL_PRODUCTS = PRODUCTS + ALL_CATEGORY_PRODUCTS


def read_csv_rows(csv_path: Path) -> list[tuple[str, int]]:
    """Read query,count rows from a CSV file."""
    if not csv_path.is_file():
        return []

    rows: list[tuple[str, int]] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return rows

        for record in reader:
            query = (record.get("query") or "").strip()
            if not query:
                continue
            try:
                count = int(record.get("count") or 0)
            except ValueError:
                continue
            rows.append((query, count))
    return rows


def _sample_count(rng: random.Random) -> int:
    """Sample search frequency from a heavy-tailed (power-law) distribution."""
    raw = rng.paretovariate(1.5)
    count = max(1, int(raw * 50))
    return min(count, 10_000_000)


def _pick_category_product(rng: random.Random) -> tuple[str, str]:
    category = rng.choice(ALL_CATEGORIES)
    product = rng.choice(CATEGORY_PRODUCTS[category])
    return category, product


def _build_iphone_query(rng: random.Random) -> str:
    style = rng.randrange(10)
    if style == 0:
        return f"iphone {rng.choice(IPHONE_MODELS)}"
    if style == 1:
        return f"iphone {rng.choice(SHOPPING_MODIFIERS)}"
    if style == 2:
        return f"{rng.choice(SHOPPING_QUALIFIERS)} iphone"
    if style == 3:
        model = rng.choice(("15 pro", "15 pro max", "14 pro"))
        return f"iphone {model} {rng.choice(('price', 'review', 'unboxing'))}"
    if style == 4:
        return f"iphone {rng.choice(ACCESSORY_MODIFIERS)}"
    if style == 5:
        model = rng.choice(IPHONE_MODELS)
        return f"iphone {model} {rng.choice(STORAGE_SIZES)} price"
    if style == 6:
        model = rng.choice(IPHONE_MODELS)
        return f"iphone {model} {rng.choice(PRICE_BANDS)}"
    if style == 7:
        city = rng.choice(INDIAN_CITIES)
        return f"iphone {rng.choice(IPHONE_MODELS)} price in {city}"
    if style == 8:
        return f"iphone {rng.choice(IPHONE_MODELS)} {rng.choice(YEARS)}"
    return "iphone"


def _build_ipl_query(rng: random.Random) -> str:
    style = rng.randrange(8)
    if style == 0:
        return "ipl live score"
    if style == 1:
        if rng.randrange(2) == 0:
            return "ipl schedule"
        return f"ipl schedule {rng.choice(YEARS)}"
    if style == 2:
        return "ipl points table"
    if style == 3:
        team_one, team_two = rng.sample(IPL_TEAMS, 2)
        return f"ipl {team_one} vs {team_two}"
    if style == 4:
        team_one, team_two = rng.sample(IPL_TEAMS, 2)
        return f"ipl {team_one} vs {team_two} {rng.choice(YEARS)}"
    if style == 5:
        return rng.choice(("ipl 2025", "ipl highlights", "ipl score today"))
    if style == 6:
        return f"ipl {rng.choice(CRICKET_VIEWING)}"
    return f"ipl {rng.choice(YEARS)} {rng.choice(CRICKET_VIEWING)}"


def _build_electronics_query(rng: random.Random) -> str:
    product = rng.choice(ELECTRONICS_PRODUCTS)
    style = rng.randrange(8)
    if style == 0:
        return f"{product} {rng.choice(DEVICE_MODIFIERS)}"
    if style == 1:
        return f"{product} {rng.choice(SHOPPING_MODIFIERS)}"
    if style == 2:
        return f"{rng.choice(SHOPPING_QUALIFIERS)} {product}"
    if style == 3:
        return f"{product} {rng.choice(ACCESSORY_MODIFIERS)}"
    if style == 4:
        return f"{product} {rng.choice(STORAGE_SIZES)} {rng.choice(SHOPPING_MODIFIERS)}"
    if style == 5:
        return f"{product} {rng.choice(YEARS)} {rng.choice(SHOPPING_MODIFIERS)}"
    if style == 6:
        return f"{product} price in {rng.choice(INDIAN_CITIES)}"
    return f"{rng.choice(SHOPPING_QUALIFIERS)} {product} {rng.choice(INDIAN_CITIES)}"


def _build_tech_query(rng: random.Random) -> str:
    product = rng.choice(TECH_PRODUCTS)
    style = rng.randrange(5)
    if style == 0:
        return f"{rng.choice(TECH_QUALIFIERS)} {product}"
    if style == 1:
        return f"{product} {rng.choice(TECH_MODIFIERS)}"
    if style == 2:
        return f"{product} {rng.choice(('guide', 'cheatsheet', 'walkthrough'))}"
    if style == 3:
        return f"{product} {rng.choice(YEARS)} {rng.choice(TECH_MODIFIERS)}"
    return f"{rng.choice(TECH_QUALIFIERS)} {product} {rng.choice(YEARS)}"


def _build_samsung_query(rng: random.Random) -> str:
    model = rng.choice(SAMSUNG_MODELS)
    style = rng.randrange(6)
    if style == 0:
        return f"samsung galaxy {model}"
    if style == 1:
        return f"samsung galaxy {model} {rng.choice(SHOPPING_MODIFIERS)}"
    if style == 2:
        return f"samsung galaxy {model} {rng.choice(STORAGE_SIZES)} price"
    if style == 3:
        return f"{rng.choice(SHOPPING_QUALIFIERS)} samsung galaxy {model}"
    if style == 4:
        return f"samsung galaxy {model} {rng.choice(ACCESSORY_MODIFIERS)}"
    city = rng.choice(INDIAN_CITIES)
    return f"samsung galaxy {model} price in {city}"


def _build_device_city_query(rng: random.Random) -> str:
    product = rng.choice(ELECTRONICS_PRODUCTS)
    city = rng.choice(INDIAN_CITIES)
    style = rng.randrange(4)
    if style == 0:
        return f"{product} price in {city}"
    if style == 1:
        return f"{product} deals {city}"
    if style == 2:
        return f"buy {product} {city}"
    return f"{product} {rng.choice(SHOPPING_MODIFIERS)} {city}"


def _build_storage_price_query(rng: random.Random) -> str:
    product = rng.choice(("iphone", "samsung galaxy", "macbook", "ipad", "laptop"))
    storage = rng.choice(STORAGE_SIZES)
    detail = rng.choice(("price", "deals", "review"))
    if product == "iphone":
        return f"iphone {rng.choice(IPHONE_MODELS)} {storage} {detail}"
    if product == "samsung galaxy":
        return f"samsung galaxy {rng.choice(SAMSUNG_MODELS)} {storage} {detail}"
    if product == "macbook":
        return f"macbook {rng.choice(MACBOOK_VARIANTS)} {storage} {detail}"
    if product == "ipad":
        return f"ipad {rng.choice(IPAD_VARIANTS)} {storage} {detail}"
    return f"{product} {storage} {rng.choice(PRICE_BANDS)}"


def _build_price_band_query(rng: random.Random) -> str:
    product = rng.choice(ALL_CATEGORY_PRODUCTS + ELECTRONICS_PRODUCTS)
    return f"{product} {rng.choice(PRICE_BANDS)}"


def _build_comparison_query(rng: random.Random) -> str:
    left, right = rng.sample(ELECTRONICS_PRODUCTS, 2)
    return f"{left} vs {right}"


def _build_exam_location_query(rng: random.Random) -> str:
    exam = rng.choice(INDIAN_EXAMS)
    style = rng.randrange(4)
    if style == 0:
        return f"{exam} {rng.choice(EXAM_SUFFIXES)}"
    if style == 1:
        return f"{exam} {rng.choice(EXAM_SUFFIXES)} {rng.choice(YEARS)}"
    if style == 2:
        return f"{exam} {rng.choice(EXAM_SUFFIXES)} {rng.choice(INDIAN_CITIES)}"
    return f"{rng.choice(SHOPPING_QUALIFIERS)} {exam} {rng.choice(EXAM_SUFFIXES)}"


def _build_travel_destination_query(rng: random.Random) -> str:
    destination = rng.choice(TRAVEL_DESTINATIONS)
    product = rng.choice(CATEGORY_PRODUCTS["Travel"])
    style = rng.randrange(4)
    if style == 0:
        return f"{product} {destination}"
    if style == 1:
        return f"{product} {destination} {rng.choice(YEARS)}"
    if style == 2:
        return f"{rng.choice(SHOPPING_QUALIFIERS)} {product} {destination}"
    return f"{product} {destination} {rng.choice(SHOPPING_MODIFIERS)}"


def _build_festival_year_query(rng: random.Random) -> str:
    festival = rng.choice(INDIAN_FESTIVALS)
    style = rng.randrange(4)
    if style == 0:
        return f"{festival} {rng.choice(YEARS)}"
    if style == 1:
        return f"{festival} {rng.choice(('ideas', 'shopping', 'recipes'))}"
    if style == 2:
        return f"{rng.choice(SHOPPING_QUALIFIERS)} {festival}"
    return f"{festival} {rng.choice(SHOPPING_MODIFIERS)}"


def _build_category_city_query(rng: random.Random) -> str:
    _category, product = _pick_category_product(rng)
    city = rng.choice(INDIAN_CITIES)
    style = rng.randrange(3)
    if style == 0:
        return f"{product} {city}"
    if style == 1:
        return f"{rng.choice(SHOPPING_QUALIFIERS)} {product} {city}"
    return f"{product} {rng.choice(SHOPPING_MODIFIERS)} {city}"


def _build_book_format_query(rng: random.Random) -> str:
    product = rng.choice(CATEGORY_PRODUCTS["Books"])
    book_format = rng.choice(BOOK_FORMATS)
    style = rng.randrange(3)
    if style == 0:
        return f"{product} {book_format}"
    if style == 1:
        return f"{rng.choice(SHOPPING_QUALIFIERS)} {product} {book_format}"
    return f"{product} {book_format} {rng.choice(SHOPPING_MODIFIERS)}"


def _build_rich_category_query(rng: random.Random) -> str:
    _category, product = _pick_category_product(rng)
    return (
        f"{rng.choice(SHOPPING_QUALIFIERS)} {product} "
        f"{rng.choice(SHOPPING_MODIFIERS)} {rng.choice(INDIAN_CITIES)}"
    )


def _build_product_year_query(rng: random.Random) -> str:
    product = rng.choice(ALL_CATEGORY_PRODUCTS + ELECTRONICS_PRODUCTS)
    return f"{product} {rng.choice(YEARS)} {rng.choice(SHOPPING_MODIFIERS)}"


def _build_clothing_query(rng: random.Random) -> str:
    product = rng.choice(CATEGORY_PRODUCTS["Clothing"])
    style = rng.randrange(5)
    if style == 0:
        return f"{product} size {rng.choice(CLOTHING_SIZES)}"
    if style == 1:
        return f"{product} {rng.choice(CLOTHING_COLORS)}"
    if style == 2:
        return f"{product} {rng.choice(CLOTHING_COLORS)} {rng.choice(INDIAN_CITIES)}"
    if style == 3:
        return (
            f"{rng.choice(SHOPPING_QUALIFIERS)} {product} "
            f"size {rng.choice(CLOTHING_SIZES)} {rng.choice(INDIAN_CITIES)}"
        )
    return f"{product} {rng.choice(SHOPPING_MODIFIERS)} {rng.choice(INDIAN_CITIES)}"


def _build_grocery_query(rng: random.Random) -> str:
    product = rng.choice(CATEGORY_PRODUCTS["Groceries"])
    style = rng.randrange(4)
    if style == 0:
        return f"{product} {rng.choice(GROCERY_SIZES)}"
    if style == 1:
        return f"{product} {rng.choice(GROCERY_SIZES)} {rng.choice(SHOPPING_MODIFIERS)}"
    if style == 2:
        return f"{rng.choice(SHOPPING_QUALIFIERS)} {product} {rng.choice(GROCERY_SIZES)}"
    return f"{product} {rng.choice(GROCERY_SIZES)} {rng.choice(INDIAN_CITIES)}"


def _build_appliance_query(rng: random.Random) -> str:
    product = rng.choice(CATEGORY_PRODUCTS["Home appliances"])
    style = rng.randrange(4)
    if style == 0:
        return f"{product} {rng.choice(AC_CAPACITIES)}"
    if style == 1:
        return f"{product} {rng.choice(AC_CAPACITIES)} {rng.choice(SHOPPING_MODIFIERS)}"
    if style == 2:
        return (
            f"{product} {rng.choice(AC_CAPACITIES)} "
            f"{rng.choice(SHOPPING_MODIFIERS)} {rng.choice(INDIAN_CITIES)}"
        )
    return f"{rng.choice(SHOPPING_QUALIFIERS)} {product} {rng.choice(INDIAN_CITIES)}"


def _build_automobile_query(rng: random.Random) -> str:
    product = rng.choice(CATEGORY_PRODUCTS["Automobiles"])
    style = rng.randrange(4)
    if style == 0:
        return f"{product} {rng.choice(BIKE_CC)}"
    if style == 1:
        return f"{product} {rng.choice(BIKE_CC)} {rng.choice(INDIAN_CITIES)}"
    if style == 2:
        return f"{product} {rng.choice(SHOPPING_MODIFIERS)} {rng.choice(INDIAN_CITIES)}"
    return f"{rng.choice(SHOPPING_QUALIFIERS)} {product} {rng.choice(YEARS)}"


def _build_laptop_brand_query(rng: random.Random) -> str:
    brand = rng.choice(LAPTOP_BRANDS)
    style = rng.randrange(4)
    if style == 0:
        return f"{brand} laptop {rng.choice(SHOPPING_MODIFIERS)}"
    if style == 1:
        return f"{brand} {rng.choice(STORAGE_SIZES)} {rng.choice(PRICE_BANDS)}"
    if style == 2:
        return f"{brand} laptop price in {rng.choice(INDIAN_CITIES)}"
    return f"{rng.choice(SHOPPING_QUALIFIERS)} {brand} laptop"


def _build_indian_tech_city_query(rng: random.Random) -> str:
    service = rng.choice(INDIAN_TECH)
    style = rng.randrange(3)
    if style == 0:
        return f"{service} {rng.choice(INDIAN_CITIES)}"
    if style == 1:
        return f"{service} {rng.choice(('offer', 'plan', 'update'))} {rng.choice(INDIAN_CITIES)}"
    return f"{rng.choice(SHOPPING_QUALIFIERS)} {service} {rng.choice(YEARS)}"


def _build_qualified_price_city_query(rng: random.Random) -> str:
    product = rng.choice(ALL_CATEGORY_PRODUCTS + ELECTRONICS_PRODUCTS)
    return (
        f"{rng.choice(SHOPPING_QUALIFIERS)} {product} "
        f"{rng.choice(PRICE_BANDS)} {rng.choice(INDIAN_CITIES)}"
    )


def _build_beauty_concern_query(rng: random.Random) -> str:
    product = rng.choice(CATEGORY_PRODUCTS["Beauty products"])
    style = rng.randrange(4)
    if style == 0:
        return f"{product} for {rng.choice(BEAUTY_CONCERNS)}"
    if style == 1:
        return f"{product} for {rng.choice(BEAUTY_CONCERNS)} {rng.choice(INDIAN_CITIES)}"
    if style == 2:
        return f"{rng.choice(SHOPPING_QUALIFIERS)} {product} {rng.choice(BEAUTY_CONCERNS)}"
    return f"{product} {rng.choice(SHOPPING_MODIFIERS)} {rng.choice(INDIAN_CITIES)}"


def _build_furniture_room_query(rng: random.Random) -> str:
    product = rng.choice(CATEGORY_PRODUCTS["Furniture"])
    room = rng.choice(FURNITURE_ROOMS)
    style = rng.randrange(4)
    if style == 0:
        return f"{product} for {room}"
    if style == 1:
        return f"{product} for {room} {rng.choice(INDIAN_CITIES)}"
    if style == 2:
        return f"{rng.choice(SHOPPING_QUALIFIERS)} {product} {room}"
    return f"{product} {room} {rng.choice(SHOPPING_MODIFIERS)} {rng.choice(INDIAN_CITIES)}"


def _build_entertainment_language_query(rng: random.Random) -> str:
    title = rng.choice(INDIAN_ENTERTAINMENT)
    style = rng.randrange(3)
    if style == 0:
        return f"{title} {rng.choice(MOVIE_LANGUAGES)}"
    if style == 1:
        return f"{title} {rng.choice(MOVIE_LANGUAGES)} {rng.choice(YEARS)}"
    return f"{title} {rng.choice(('review', 'trailer'))} {rng.choice(MOVIE_LANGUAGES)}"


def _build_category_shopping_query(rng: random.Random) -> str:
    category, product = _pick_category_product(rng)
    style = rng.randrange(3)
    if style == 0:
        return f"{category.lower()} {product}"
    if style == 1:
        return f"{rng.choice(SHOPPING_QUALIFIERS)} {product}"
    return f"{product} {rng.choice(SHOPPING_MODIFIERS)}"


def _build_query(rng: random.Random, pattern: int) -> str:
    if pattern == 0:
        return _build_iphone_query(rng)
    if pattern == 1:
        return _build_electronics_query(rng)
    if pattern == 2:
        return _build_category_shopping_query(rng)
    if pattern == 3:
        return _build_ipl_query(rng)
    if pattern == 4:
        return (
            f"{rng.choice(INDIAN_CRICKET)} "
            f"{rng.choice(('highlights', 'schedule', 'ticket booking'))}"
        )
    if pattern == 5:
        return f"{rng.choice(SHOPPING_QUALIFIERS)} {rng.choice(INDIAN_CRICKET)}"
    if pattern == 6:
        return _build_exam_location_query(rng)
    if pattern == 7:
        return _build_festival_year_query(rng)
    if pattern == 8:
        return (
            f"{rng.choice(INDIAN_ENTERTAINMENT)} "
            f"{rng.choice(('review', 'trailer', 'tickets'))}"
        )
    if pattern == 9:
        return _build_tech_query(rng)
    if pattern == 10:
        return f"{rng.choice(INDIAN_TECH)} {rng.choice(('offer', 'plan', 'update'))}"
    if pattern == 11:
        category, product = _pick_category_product(rng)
        return f"{rng.choice(SHOPPING_QUALIFIERS)} {product} {category.lower()}"
    if pattern == 12:
        product = rng.choice(ALL_CATEGORY_PRODUCTS)
        return f"{product} {rng.choice(SHOPPING_MODIFIERS)}"
    if pattern == 13:
        return f"{rng.choice(INDIAN_FESTIVALS)} {rng.choice(SHOPPING_MODIFIERS)}"
    if pattern == 14:
        return f"{rng.choice(INDIAN_ENTERTAINMENT)} {rng.choice(SHOPPING_MODIFIERS)}"
    if pattern == 15:
        return _build_samsung_query(rng)
    if pattern == 16:
        return _build_device_city_query(rng)
    if pattern == 17:
        return _build_storage_price_query(rng)
    if pattern == 18:
        return _build_price_band_query(rng)
    if pattern == 19:
        return _build_comparison_query(rng)
    if pattern == 20:
        return _build_travel_destination_query(rng)
    if pattern == 21:
        return _build_category_city_query(rng)
    if pattern == 22:
        return _build_book_format_query(rng)
    if pattern == 23:
        cricket = rng.choice(INDIAN_CRICKET)
        return f"{cricket} {rng.choice(YEARS)} {rng.choice(('highlights', 'schedule'))}"
    if pattern == 24:
        product = rng.choice(ELECTRONICS_PRODUCTS)
        return f"{product} {rng.choice(DEVICE_MODIFIERS)} {rng.choice(SHOPPING_MODIFIERS)}"
    if pattern == 25:
        return _build_rich_category_query(rng)
    if pattern == 26:
        return _build_product_year_query(rng)
    if pattern == 27:
        return _build_clothing_query(rng)
    if pattern == 28:
        return _build_grocery_query(rng)
    if pattern == 29:
        return _build_appliance_query(rng)
    if pattern == 30:
        return _build_automobile_query(rng)
    if pattern == 31:
        return _build_laptop_brand_query(rng)
    if pattern == 32:
        return _build_indian_tech_city_query(rng)
    if pattern == 33:
        return _build_qualified_price_city_query(rng)
    if pattern == 34:
        return _build_beauty_concern_query(rng)
    if pattern == 35:
        return _build_furniture_room_query(rng)
    if pattern == 36:
        return _build_entertainment_language_query(rng)
    if pattern == 37:
        cricket = rng.choice(INDIAN_CRICKET)
        return f"{cricket} {rng.choice(YEARS)} {rng.choice(CRICKET_VIEWING)}"
    product = rng.choice(ALL_CATEGORY_PRODUCTS)
    return f"{product} {rng.choice(YEARS)} {rng.choice(SHOPPING_MODIFIERS)}"


def estimate_minimum_template_cardinality() -> int:
    """Conservative lower bound on distinct queries the templates can emit."""
    ipl_matchups = len(IPL_TEAMS) * (len(IPL_TEAMS) - 1)
    electronics = len(ELECTRONICS_PRODUCTS)
    category_products = len(ALL_CATEGORY_PRODUCTS)

    total = 0
    total += len(IPHONE_MODELS) * (
        len(STORAGE_SIZES) + len(SHOPPING_MODIFIERS) + len(INDIAN_CITIES) + len(PRICE_BANDS)
    )
    total += ipl_matchups * (len(YEARS) + len(CRICKET_VIEWING))
    total += electronics * (electronics - 1)
    total += category_products * len(INDIAN_CITIES) * len(SHOPPING_MODIFIERS)
    total += len(INDIAN_EXAMS) * len(EXAM_SUFFIXES) * len(YEARS)
    total += len(CATEGORY_PRODUCTS["Travel"]) * len(TRAVEL_DESTINATIONS) * len(YEARS)
    total += len(SAMSUNG_MODELS) * (len(STORAGE_SIZES) + len(SHOPPING_MODIFIERS) + len(INDIAN_CITIES))
    total += category_products * len(PRICE_BANDS)
    total += len(INDIAN_FESTIVALS) * len(YEARS) * len(SHOPPING_MODIFIERS)
    total += len(TECH_PRODUCTS) * len(TECH_QUALIFIERS) * len(TECH_MODIFIERS)
    total += len(CATEGORY_PRODUCTS["Books"]) * len(BOOK_FORMATS) * len(SHOPPING_MODIFIERS)
    total += category_products * len(SHOPPING_QUALIFIERS) * len(SHOPPING_MODIFIERS) * len(INDIAN_CITIES)
    total += len(CATEGORY_PRODUCTS["Clothing"]) * len(CLOTHING_SIZES) * len(CLOTHING_COLORS) * len(INDIAN_CITIES)
    total += len(CATEGORY_PRODUCTS["Groceries"]) * len(GROCERY_SIZES) * len(INDIAN_CITIES)
    total += len(CATEGORY_PRODUCTS["Home appliances"]) * len(AC_CAPACITIES) * len(INDIAN_CITIES)
    total += len(LAPTOP_BRANDS) * len(STORAGE_SIZES) * len(INDIAN_CITIES)
    total += (category_products + electronics) * len(SHOPPING_QUALIFIERS) * len(PRICE_BANDS) * len(INDIAN_CITIES)
    total += len(CATEGORY_PRODUCTS["Beauty products"]) * len(BEAUTY_CONCERNS) * len(INDIAN_CITIES)
    total += len(CATEGORY_PRODUCTS["Furniture"]) * len(FURNITURE_ROOMS) * len(INDIAN_CITIES)
    return total


def generate_synthetic_queries(target_count: int, seed: int = 42) -> list[tuple[str, int]]:
    """Generate realistic unique search queries with frequency counts."""
    rng = random.Random(seed)
    queries: dict[str, int] = {}
    pattern_count = 38
    max_attempts = target_count * 20
    attempts = 0

    while len(queries) < target_count and attempts < max_attempts:
        attempts += 1
        pattern = rng.randrange(pattern_count)
        query = _build_query(rng, pattern)
        query = " ".join(query.split())
        if query and query not in queries:
            queries[query] = _sample_count(rng)

    if len(queries) < target_count:
        raise RuntimeError(
            f"Could only generate {len(queries)} unique queries; target was {target_count}"
        )

    return list(queries.items())


def load_rows(
    csv_path: Path,
    min_rows: int = MIN_QUERY_COUNT,
    seed: int = 42,
) -> list[tuple[str, int]]:
    """Combine CSV data with synthetic queries until min_rows is reached."""
    rows = read_csv_rows(csv_path)
    existing = {query for query, _ in rows}

    if len(rows) < min_rows:
        needed = min_rows - len(rows)
        synthetic = generate_synthetic_queries(needed, seed=seed)
        for query, count in synthetic:
            if query not in existing:
                rows.append((query, count))
                existing.add(query)

    return rows


def load_in_batches(rows: list[tuple[str, int]], db_path: Path) -> int:
    """Insert rows in batches for efficient bulk loading."""
    total_inserted = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        total_inserted += bulk_insert_queries(batch, db_path)
    return total_inserted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load search queries into SQLite.")
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"CSV file with query,count columns (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(DATABASE_PATH),
        help=f"SQLite database path (default: {DATABASE_PATH})",
    )
    parser.add_argument(
        "--min-rows",
        type=int,
        default=MIN_QUERY_COUNT,
        help=f"Minimum queries to load (default: {MIN_QUERY_COUNT})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for synthetic query generation",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = args.db.resolve()
    csv_path = args.csv.resolve()

    rows = load_rows(csv_path, min_rows=args.min_rows, seed=args.seed)
    if len(rows) < args.min_rows:
        raise SystemExit(
            f"Expected at least {args.min_rows} queries, prepared {len(rows)}"
        )

    init_db(db_path)
    inserted = load_in_batches(rows, db_path)
    total = get_row_count(db_path)

    print(f"Prepared {len(rows)} queries from {csv_path.name}")
    print(f"Inserted {inserted} new rows into {db_path}")
    print(f"Total rows in database: {total}")


if __name__ == "__main__":
    main()
