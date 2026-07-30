from fastapi import APIRouter, HTTPException, Response

from app.collectors.google_places import run_google_discovery, run_nearby_discovery, sync_google
from app.collectors.meta_ads import sync_meta
from app.collectors.swiggy import sync_swiggy
from app.collectors.zomato import sync_zomato
from app.config import settings
from app.database.mongo import get_restaurants_db, save_restaurant
from app.exports.csv_export import build_csv
from app.models import AssignLeadsPayload, DistrictCheckPayload, FlagUpdatePayload, MetaUpdatePayload, NearbySearchPayload, ZomatoUpdatePayload
from app.scoring.lead_score import calculate_scores
from app.services import (
    build_dashboard_stats,
    current_timestamp,
    district_due_for_check,
    meta_due_for_check,
    recompute_lead_score,
    swiggy_due_for_check,
)

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/restaurants")
def list_restaurants():
    return list(get_restaurants_db().values())


@router.get("/restaurants/saved")
def list_saved_restaurants():
    """The 'Add to Cart' list: restaurants explicitly saved by the sales team,
    read back from the database (not just client-side state)."""
    return [r for r in get_restaurants_db().values() if r.get("lead", {}).get("saved")]


@router.get("/restaurants/{restaurant_id}")
def get_restaurant(restaurant_id: str):
    restaurant = get_restaurants_db().get(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant


@router.patch("/restaurants/{restaurant_id}/flags")
def update_restaurant_flags(restaurant_id: str, payload: FlagUpdatePayload):
    restaurant = get_restaurants_db().get(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    restaurant.setdefault("lead", {})
    if payload.read is not None:
        restaurant["lead"]["read"] = payload.read
    if payload.important is not None:
        restaurant["lead"]["important"] = payload.important
    if payload.saved is not None:
        restaurant["lead"]["saved"] = payload.saved
    save_restaurant(restaurant)
    return restaurant


@router.post("/check-district")
def update_district(payload: DistrictCheckPayload):
    restaurant = get_restaurants_db().get(payload.restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    restaurant["district"]["checked"] = True
    restaurant["district"]["onboarded"] = payload.onboarded
    restaurant["district"]["payBill"] = payload.pay_bill
    restaurant["district"]["lastChecked"] = current_timestamp()
    recompute_lead_score(restaurant)
    save_restaurant(restaurant)
    return restaurant


@router.post("/sync-google")
def sync_google_endpoint(payload: dict):
    city = payload.get("city", "Goa")
    restaurants = payload.get("restaurants", [])
    return sync_google(city, restaurants)


@router.post("/discover-google")
def discover_google_endpoint(payload: dict | None = None):
    """Trigger a live Google Places discovery sweep. Requires GOOGLE_MAPS_API_KEY."""
    payload = payload or {}
    cities = payload.get("cities")
    keywords = payload.get("keywords")
    try:
        return run_google_discovery(cities, keywords)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/sync-meta")
def sync_meta_endpoint(payload: MetaUpdatePayload):
    return sync_meta(payload.restaurant_id, payload.running_ads, payload.instagram_page, payload.facebook_page)


@router.post("/sync-swiggy")
def sync_swiggy_endpoint(payload: dict):
    return sync_swiggy(payload["restaurant_id"], payload.get("available", False))


@router.post("/sync-zomato")
def sync_zomato_endpoint(payload: ZomatoUpdatePayload):
    return sync_zomato(payload.restaurant_id, payload.listed)


@router.post("/search-nearby")
def search_nearby_endpoint(payload: NearbySearchPayload):
    """Search Google Places within radius_km (capped at 50km, Google's Nearby
    Search maximum) of an exact place typed by the user, and upsert results."""
    try:
        return run_nearby_discovery(payload.place, payload.radius_km, payload.keywords)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/assign-leads")
def assign_leads(payload: AssignLeadsPayload):
    """Mark restaurants as already assigned to a salesperson so they are
    excluded from future exports (avoids double-contacting an outlet)."""
    db = get_restaurants_db()
    assigned = []
    for restaurant_id in payload.restaurant_ids:
        restaurant = db.get(restaurant_id)
        if not restaurant:
            continue
        restaurant.setdefault("lead", {})
        restaurant["lead"]["assignedTo"] = payload.assigned_to or "assigned"
        restaurant["lead"]["exported"] = True
        save_restaurant(restaurant)
        assigned.append(restaurant_id)
    return {"assigned": assigned}


@router.get("/leads/due-for-check")
def leads_due_for_check():
    restaurants = list(get_restaurants_db().values())
    return {
        "district": [r["_id"] for r in restaurants if district_due_for_check(r, settings.district_recheck_days)],
        "meta": [r["_id"] for r in restaurants if meta_due_for_check(r, settings.meta_recheck_days)],
        "swiggy": [r["_id"] for r in restaurants if swiggy_due_for_check(r, settings.swiggy_recheck_days)],
    }


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
def export_csv(exclude_assigned: bool = True):
    csv_content = build_csv(exclude_assigned=exclude_assigned)
    return Response(content=csv_content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=restaurants.csv"})
