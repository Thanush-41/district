import csv
import io
from app.database.mongo import get_restaurants_db


def build_csv(exclude_assigned: bool = True) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["restaurant_id", "name", "phone", "instagram", "website", "district_status", "rating", "reviews", "lead_score", "priority"])
    writer.writeheader()
    for restaurant_id, restaurant in get_restaurants_db().items():
        if exclude_assigned and restaurant.get("lead", {}).get("assignedTo"):
            continue
        writer.writerow(
            {
                "restaurant_id": restaurant_id,
                "name": restaurant.get("google", {}).get("name", ""),
                "phone": restaurant.get("google", {}).get("phone", ""),
                "instagram": restaurant.get("metaAds", {}).get("instagramPage", ""),
                "website": restaurant.get("google", {}).get("website", ""),
                "district_status": "onboarded" if restaurant.get("district", {}).get("onboarded", False) else "not onboarded",
                "rating": restaurant.get("google", {}).get("rating", ""),
                "reviews": restaurant.get("google", {}).get("reviews", ""),
                "lead_score": restaurant.get("lead", {}).get("score", 0),
                "priority": restaurant.get("lead", {}).get("priority", "LOW"),
            }
        )
    return output.getvalue()
