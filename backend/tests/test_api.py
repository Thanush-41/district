import pytest
from fastapi.testclient import TestClient

from app.database.mongo import reset_store
from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    reset_store()
    yield


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_restaurants_and_dashboard_stats():
    response = client.get("/restaurants")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 1

    stats = client.get("/dashboard/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert body["total_restaurants"] >= 1
    assert body["not_onboarded"] >= 0
    assert body["high_priority_leads"] >= 0


def test_district_and_meta_updates_and_export():
    restaurant_id = "restaurant-1"

    update_response = client.post(
        "/check-district",
        json={"restaurant_id": restaurant_id, "onboarded": True, "pay_bill": True},
    )
    assert update_response.status_code == 200

    meta_response = client.post(
        "/sync-meta",
        json={"restaurant_id": restaurant_id, "running_ads": True, "instagram_page": "@cafe"},
    )
    assert meta_response.status_code == 200

    restaurant = client.get(f"/restaurants/{restaurant_id}")
    assert restaurant.status_code == 200
    payload = restaurant.json()
    assert payload["district"]["onboarded"] is True
    assert payload["metaAds"]["runningAds"] is True

    high_leads = client.get("/high-priority-leads")
    assert high_leads.status_code == 200
    assert len(high_leads.json()) >= 0

    export = client.get("/export")
    assert export.status_code == 200
    assert "text/csv" in export.headers["content-type"]
    assert "restaurant_id" in export.text


def test_google_sync_marks_new_restaurants_and_running_ads_filters():
    sync_response = client.post(
        "/sync-google",
        json={
            "city": "Panaji",
            "restaurants": [
                {
                    "place_id": "place-2",
                    "name": "Bite & Brew",
                    "address": "Panaji, Goa",
                    "rating": 4.7,
                    "reviews": 1300,
                    "phone": "+91-99999",
                    "website": "https://bite.com",
                    "business_status": "OPERATIONAL",
                }
            ],
        },
    )
    assert sync_response.status_code == 200
    body = sync_response.json()
    assert body["created"] >= 1
    assert body["updated"] >= 0

    new_restaurants = client.get("/new-restaurants")
    assert new_restaurants.status_code == 200
    assert len(new_restaurants.json()) >= 1

    running_ads = client.get("/running-ads")
    assert running_ads.status_code == 200
    assert isinstance(running_ads.json(), list)
