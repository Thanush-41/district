from typing import Dict

from app.database.mongo import get_restaurants_db, save_restaurant
from app.services import recompute_lead_score


def sync_meta(restaurant_id: str, running_ads: bool, instagram_page: str | None = None, facebook_page: str | None = None) -> dict:
    db = get_restaurants_db()
    restaurant = db.get(restaurant_id)
    if restaurant is None:
        raise KeyError("restaurant not found")

    restaurant["metaAds"]["runningAds"] = running_ads
    restaurant["metaAds"]["facebookPage"] = facebook_page
    restaurant["metaAds"]["instagramPage"] = instagram_page
    restaurant["metaAds"]["lastSeen"] = "2026-07-25"
    recompute_lead_score(restaurant)
    save_restaurant(restaurant)
    return restaurant
