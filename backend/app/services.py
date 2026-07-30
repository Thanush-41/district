from datetime import datetime, timezone
from typing import Optional


def recompute_lead_score(restaurant: dict) -> dict:
    score = 0
    if not restaurant.get("district", {}).get("onboarded", False):
        score += 100
    if restaurant.get("metaAds", {}).get("runningAds", False):
        score += 40
    if restaurant.get("isNew", False):
        score += 30
    if restaurant.get("swiggy", {}).get("available", False):
        score += 20
    if restaurant.get("google", {}).get("website"):
        score += 15
    if restaurant.get("metaAds", {}).get("instagramPage"):
        score += 10
    if (restaurant.get("google", {}).get("rating") or 0) > 4.3:
        score += 10
    if (restaurant.get("google", {}).get("reviews") or 0) > 500:
        score += 20

    priority = "LOW"
    if score >= 200:
        priority = "HIGH"
    elif score >= 100:
        priority = "MEDIUM"

    restaurant.setdefault("lead", {})
    restaurant["lead"]["score"] = score
    restaurant["lead"]["priority"] = priority
    return restaurant


def build_dashboard_stats(restaurants: list[dict]) -> dict:
    not_onboarded = sum(1 for restaurant in restaurants if not restaurant.get("district", {}).get("onboarded", False))
    high_priority = sum(1 for restaurant in restaurants if restaurant.get("lead", {}).get("priority") == "HIGH")
    return {
        "total_restaurants": len(restaurants),
        "not_onboarded": not_onboarded,
        "running_ads": sum(1 for restaurant in restaurants if restaurant.get("metaAds", {}).get("runningAds", False)),
        "high_priority_leads": high_priority,
        "new_restaurants": sum(1 for restaurant in restaurants if restaurant.get("isNew", False)),
    }


def current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_timestamp(value: Optional[str]):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _is_due(last_timestamp: Optional[str], days: int) -> bool:
    parsed = _parse_timestamp(last_timestamp)
    if parsed is None:
        return True
    return (datetime.now(timezone.utc) - parsed).days >= days


def district_due_for_check(restaurant: dict, days: int) -> bool:
    district = restaurant.get("district", {})
    if not district.get("checked", False):
        return True
    return _is_due(district.get("lastChecked"), days)


def meta_due_for_check(restaurant: dict, days: int) -> bool:
    return _is_due(restaurant.get("metaAds", {}).get("lastSeen"), days)


def swiggy_due_for_check(restaurant: dict, days: int) -> bool:
    return _is_due(restaurant.get("swiggy", {}).get("lastChecked"), days)
