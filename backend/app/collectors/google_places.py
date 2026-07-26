from typing import List

from app.database.mongo import get_restaurants_db, save_restaurant
from app.services import recompute_lead_score


def sync_google(city: str, restaurants: List[dict]) -> dict:
    created = 0
    updated = 0

    for item in restaurants:
        place_id = item.get("place_id") or item.get("placeId")
        if not place_id:
            continue

        db = get_restaurants_db()
        restaurant = db.get(place_id)
        if restaurant is None:
            restaurant = {
                "_id": place_id,
                "google": {},
                "district": {"checked": False, "onboarded": False, "payBill": False, "lastChecked": None},
                "metaAds": {"runningAds": False, "facebookPage": None, "instagramPage": None, "lastSeen": None},
                "swiggy": {"available": False, "dineout": False},
                "lead": {"score": 0, "priority": "LOW", "assignedTo": None, "exported": False},
                "isNew": True,
            }
            created += 1
            db[place_id] = restaurant
        else:
            updated += 1
            restaurant["isNew"] = False

        restaurant["google"].update(
            {
                "placeId": place_id,
                "name": item.get("name"),
                "address": item.get("address"),
                "rating": item.get("rating"),
                "reviews": item.get("reviews"),
                "phone": item.get("phone"),
                "website": item.get("website"),
                "businessStatus": item.get("business_status") or item.get("businessStatus"),
                "city": city,
            }
        )
        restaurant["isNew"] = restaurant.get("isNew", False)
        recompute_lead_score(restaurant)
        save_restaurant(restaurant)

    return {"created": created, "updated": updated, "city": city}
