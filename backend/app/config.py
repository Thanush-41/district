import os
from dataclasses import dataclass, field
from typing import List

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - optional dependency fallback
    pass

DEFAULT_CITIES = ["Panaji", "Margao", "Calangute", "Candolim", "Baga", "Mapusa", "Anjuna", "Vasco", "Porvorim"]
DEFAULT_KEYWORDS = ["restaurant", "cafe", "bar", "pub", "bakery", "fine dining", "seafood", "pizza"]


def _split_csv_env(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name)
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass
class Settings:
    mongo_uri: str = field(default_factory=lambda: os.getenv("MONGO_URI", ""))
    mongo_db_name: str = field(default_factory=lambda: os.getenv("MONGO_DB_NAME", "district"))
    google_maps_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_MAPS_API_KEY", ""))
    google_fetch_details: bool = field(default_factory=lambda: os.getenv("GOOGLE_FETCH_DETAILS", "true").lower() == "true")
    search_cities: List[str] = field(default_factory=lambda: _split_csv_env("SEARCH_CITIES", DEFAULT_CITIES))
    search_keywords: List[str] = field(default_factory=lambda: _split_csv_env("SEARCH_KEYWORDS", DEFAULT_KEYWORDS))
    district_recheck_days: int = field(default_factory=lambda: int(os.getenv("DISTRICT_RECHECK_DAYS", "30")))
    meta_recheck_days: int = field(default_factory=lambda: int(os.getenv("META_RECHECK_DAYS", "3")))
    swiggy_recheck_days: int = field(default_factory=lambda: int(os.getenv("SWIGGY_RECHECK_DAYS", "7")))
    scheduler_hour_utc: int = field(default_factory=lambda: int(os.getenv("SCHEDULER_HOUR_UTC", "2")))


settings = Settings()
