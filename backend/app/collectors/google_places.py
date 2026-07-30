import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

import requests

from app.config import settings
from app.database.mongo import get_restaurants_db, save_restaurant
from app.services import recompute_lead_score

TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
FIND_PLACE_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
NEARBY_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
MAX_NEARBY_RADIUS_M = 50000  # Google's documented maximum radius for Nearby Search


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
                "swiggy": {"available": False, "dineout": False, "lastChecked": None},
                "zomato": {"listed": False, "lastChecked": None},
                "lead": {"score": 0, "priority": "LOW", "assignedTo": None, "exported": False, "read": False, "important": False, "saved": False},
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
                "city": item.get("city") or city,
            }
        )
        restaurant["isNew"] = restaurant.get("isNew", False)
        recompute_lead_score(restaurant)
        save_restaurant(restaurant)

    return {"created": created, "updated": updated, "city": city}


def _text_search(query: str, api_key: str) -> List[dict]:
    """Call the Google Places Text Search API and follow pagination tokens."""
    places: List[dict] = []
    params = {"query": query, "key": api_key}
    is_first_page = True
    for _ in range(3):  # Google caps text search at 3 pages (60 results) per query
        response = requests.get(TEXT_SEARCH_URL, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        status = payload.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            if is_first_page:
                raise RuntimeError(f"Google Places API error for '{query}': {status} - {payload.get('error_message', '')}")
            # A pagetoken request can transiently fail with INVALID_REQUEST if
            # Google hasn't activated the token yet. Treat later pages as
            # best-effort and just stop paginating instead of failing the
            # whole discovery run.
            break
        places.extend(payload.get("results", []))
        next_token = payload.get("next_page_token")
        if not next_token:
            break
        time.sleep(2.5)  # next_page_token is not valid until a short delay has passed
        params = {"pagetoken": next_token, "key": api_key}
        is_first_page = False
    return places


def _fetch_place_details(place_id: str, api_key: str) -> dict:
    params = {
        "place_id": place_id,
        "fields": "formatted_phone_number,website",
        "key": api_key,
    }
    response = requests.get(DETAILS_URL, params=params, timeout=10)
    response.raise_for_status()
    payload = response.json()
    return payload.get("result", {})


def _fetch_details_concurrently(place_ids: List[str], api_key: str, max_workers: int = 10) -> dict:
    """Fetch Place Details for many place_ids in parallel. Sequential detail
    calls are the main reason discovery/search could take minutes for a
    radius with hundreds of results, since each one is a separate network
    round-trip."""
    details_by_id: dict = {}
    if not place_ids:
        return details_by_id
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {executor.submit(_fetch_place_details, place_id, api_key): place_id for place_id in place_ids}
        for future in future_to_id:
            place_id = future_to_id[future]
            try:
                details_by_id[place_id] = future.result()
            except requests.RequestException:
                details_by_id[place_id] = {}
    return details_by_id


def fetch_places_from_google(
    cities: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    fetch_details: Optional[bool] = None,
) -> List[dict]:
    """Search Google Places (Text Search) across cities x keywords and return
    normalized restaurant dicts, deduplicated by place_id."""
    api_key = api_key or settings.google_maps_api_key
    if not api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is not configured")

    cities = cities or settings.search_cities
    keywords = keywords or settings.search_keywords
    fetch_details = settings.google_fetch_details if fetch_details is None else fetch_details

    queries = [
        (city, f"{keyword} in {city}" if city.strip().lower() == "goa" else f"{keyword} in {city}, Goa")
        for city in cities
        for keyword in keywords
    ]

    by_place_id: dict = {}
    with ThreadPoolExecutor(max_workers=min(8, len(queries) or 1)) as executor:
        future_to_city = {executor.submit(_text_search, query, api_key): city for city, query in queries}
        for future in future_to_city:
            city = future_to_city[future]
            for place in future.result():
                place_id = place.get("place_id")
                if not place_id or place_id in by_place_id:
                    continue
                by_place_id[place_id] = {
                    "place_id": place_id,
                    "name": place.get("name"),
                    "address": place.get("formatted_address"),
                    "rating": place.get("rating"),
                    "reviews": place.get("user_ratings_total"),
                    "business_status": place.get("business_status"),
                    "phone": None,
                    "website": None,
                    "city": city,
                }

    if fetch_details:
        details_by_id = _fetch_details_concurrently(list(by_place_id.keys()), api_key)
        for place_id, details in details_by_id.items():
            by_place_id[place_id]["phone"] = details.get("formatted_phone_number")
            by_place_id[place_id]["website"] = details.get("website")

    return list(by_place_id.values())


def run_google_discovery(cities: Optional[List[str]] = None, keywords: Optional[List[str]] = None) -> dict:
    """Fetch restaurants from Google Places and upsert them into the store."""
    places = fetch_places_from_google(cities, keywords)
    return sync_google("Goa", places)


def _find_place_location(place: str, api_key: str) -> Optional[dict]:
    """Resolve a free-text place into lat/lng using Places Find Place From Text."""
    params = {
        "input": place,
        "inputtype": "textquery",
        "fields": "geometry,name,formatted_address",
        "key": api_key,
    }
    response = requests.get(FIND_PLACE_URL, params=params, timeout=10)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "OK" or not payload.get("candidates"):
        return None
    candidate = payload["candidates"][0]
    location = candidate.get("geometry", {}).get("location")
    if not location:
        return None
    return {"lat": location["lat"], "lng": location["lng"], "name": candidate.get("name") or place}


def _nearby_search(lat: float, lng: float, radius_m: int, keyword: str, api_key: str) -> List[dict]:
    """Call the Google Places Nearby Search API and follow pagination tokens."""
    places: List[dict] = []
    params = {"location": f"{lat},{lng}", "radius": radius_m, "keyword": keyword, "type": "restaurant", "key": api_key}
    is_first_page = True
    for _ in range(3):
        response = requests.get(NEARBY_SEARCH_URL, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        status = payload.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            if is_first_page:
                raise RuntimeError(f"Google Places API error for nearby '{keyword}': {status} - {payload.get('error_message', '')}")
            break
        places.extend(payload.get("results", []))
        next_token = payload.get("next_page_token")
        if not next_token:
            break
        time.sleep(2.5)
        params = {"pagetoken": next_token, "key": api_key}
        is_first_page = False
    return places


def search_nearby_places(
    place: str,
    radius_km: float = 60,
    keywords: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    fetch_details: Optional[bool] = None,
) -> dict:
    """Resolve `place` to a location, then search Google Places within `radius_km`
    (clamped to Google's documented 50km Nearby Search maximum) across keywords.
    Returns the resolved location plus the normalized, deduplicated restaurant list."""
    api_key = api_key or settings.google_maps_api_key
    if not api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is not configured")

    location = _find_place_location(place, api_key)
    if location is None:
        raise RuntimeError(f"Could not resolve '{place}' to a location via Google Places")

    keywords = keywords or settings.search_keywords
    fetch_details = settings.google_fetch_details if fetch_details is None else fetch_details
    radius_m = min(int(radius_km * 1000), MAX_NEARBY_RADIUS_M)

    by_place_id: dict = {}
    with ThreadPoolExecutor(max_workers=min(8, len(keywords) or 1)) as executor:
        futures = [executor.submit(_nearby_search, location["lat"], location["lng"], radius_m, keyword, api_key) for keyword in keywords]
        for future in futures:
            for result in future.result():
                place_id = result.get("place_id")
                if not place_id or place_id in by_place_id:
                    continue
                by_place_id[place_id] = {
                    "place_id": place_id,
                    "name": result.get("name"),
                    "address": result.get("vicinity") or result.get("formatted_address"),
                    "rating": result.get("rating"),
                    "reviews": result.get("user_ratings_total"),
                    "business_status": result.get("business_status"),
                    "phone": None,
                    "website": None,
                    "city": location["name"],
                }

    if fetch_details:
        details_by_id = _fetch_details_concurrently(list(by_place_id.keys()), api_key)
        for place_id, details in details_by_id.items():
            by_place_id[place_id]["phone"] = details.get("formatted_phone_number")
            by_place_id[place_id]["website"] = details.get("website")

    return {
        "resolved_location": location,
        "radius_km": radius_m / 1000,
        "places": list(by_place_id.values()),
    }


def run_nearby_discovery(place: str, radius_km: float = 60, keywords: Optional[List[str]] = None) -> dict:
    """Search around `place` and upsert the results into the store."""
    result = search_nearby_places(place, radius_km, keywords)
    sync_result = sync_google(result["resolved_location"]["name"], result["places"])
    return {**sync_result, "radius_km": result["radius_km"], "resolved_location": result["resolved_location"]}
