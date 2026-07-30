from app.database.mongo import get_restaurants_db, save_restaurant
from app.services import current_timestamp, recompute_lead_score


def sync_zomato(restaurant_id: str, listed: bool) -> dict:
    db = get_restaurants_db()
    restaurant = db.get(restaurant_id)
    if restaurant is None:
        raise KeyError("restaurant not found")

    restaurant.setdefault("zomato", {})
    restaurant["zomato"]["listed"] = listed
    restaurant["zomato"]["lastChecked"] = current_timestamp()
    recompute_lead_score(restaurant)
    save_restaurant(restaurant)
    return restaurant
