def recompute_lead_score(restaurant: dict) -> dict:
    score = 0
    if not restaurant.get("district", {}).get("onboarded", False):
        score += 100
    if restaurant.get("metaAds", {}).get("runningAds", False):
        score += 40
    if restaurant.get("swiggy", {}).get("available", False):
        score += 30
    if restaurant.get("google", {}).get("reviews", 0) > 500:
        score += 20
    if restaurant.get("google", {}).get("website"):
        score += 15
    if restaurant.get("metaAds", {}).get("instagramPage"):
        score += 15
    if restaurant.get("google", {}).get("rating", 0) > 4.3:
        score += 10

    priority = "LOW"
    if score >= 150:
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
    }
