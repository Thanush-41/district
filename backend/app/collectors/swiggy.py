from app.database.mongo import get_restaurants_db, save_restaurant
from app.services import recompute_lead_score


def sync_swiggy(restaurant_id: str, available: bool) -> dict:
    db = get_restaurants_db()
    restaurant = db.get(restaurant_id)
    if restaurant is None:
        raise KeyError("restaurant not found")

    restaurant["swiggy"]["available"] = available
    restaurant["swiggy"]["dineout"] = available
    recompute_lead_score(restaurant)
    save_restaurant(restaurant)
    return restaurant
