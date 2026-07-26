from fastapi import APIRouter, HTTPException, Response

from app.collectors.google_places import sync_google
from app.collectors.meta_ads import sync_meta
from app.collectors.swiggy import sync_swiggy
from app.database.mongo import get_restaurants_db, save_restaurant
from app.exports.csv_export import build_csv
from app.models import DistrictCheckPayload, MetaUpdatePayload
from app.scoring.lead_score import calculate_scores
from app.services import build_dashboard_stats, recompute_lead_score

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/restaurants")
def list_restaurants():
    return list(get_restaurants_db().values())


@router.get("/restaurants/{restaurant_id}")
def get_restaurant(restaurant_id: str):
    restaurant = get_restaurants_db().get(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant


@router.post("/check-district")
def update_district(payload: DistrictCheckPayload):
    restaurant = get_restaurants_db().get(payload.restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    restaurant["district"]["checked"] = True
    restaurant["district"]["onboarded"] = payload.onboarded
    restaurant["district"]["payBill"] = payload.pay_bill
    restaurant["district"]["lastChecked"] = "2026-07-25"
    recompute_lead_score(restaurant)
    save_restaurant(restaurant)
    return restaurant


@router.post("/sync-google")
def sync_google_endpoint(payload: dict):
    city = payload.get("city", "Goa")
    restaurants = payload.get("restaurants", [])
    return sync_google(city, restaurants)


@router.post("/sync-meta")
def sync_meta_endpoint(payload: MetaUpdatePayload):
    return sync_meta(payload.restaurant_id, payload.running_ads, payload.instagram_page, payload.facebook_page)


@router.post("/sync-swiggy")
def sync_swiggy_endpoint(payload: dict):
    return sync_swiggy(payload["restaurant_id"], payload.get("available", False))


@router.get("/new-restaurants")
def new_restaurants():
    return [restaurant for restaurant in get_restaurants_db().values() if restaurant.get("isNew")]


@router.get("/high-priority-leads")
def high_priority_leads():
    return [restaurant for restaurant in get_restaurants_db().values() if restaurant.get("lead", {}).get("priority") == "HIGH"]


@router.get("/running-ads")
def running_ads():
    return [restaurant for restaurant in get_restaurants_db().values() if restaurant.get("metaAds", {}).get("runningAds")]


@router.get("/dashboard/stats")
def dashboard_stats():
    return build_dashboard_stats(list(get_restaurants_db().values()))


@router.get("/export")
def export_csv():
    csv_content = build_csv()
    return Response(content=csv_content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=restaurants.csv"})
