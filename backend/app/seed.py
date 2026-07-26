def seed_restaurants() -> dict:
    return {
        "restaurant-1": {
            "_id": "restaurant-1",
            "google": {
                "name": "Cafe Mocha",
                "placeId": "place-1",
                "address": "Panjim, Goa",
                "rating": 4.6,
                "reviews": 712,
                "phone": "+91xxxxxxxxxx",
                "website": "https://example.com",
                "businessStatus": "OPERATIONAL",
            },
            "district": {"checked": True, "onboarded": False, "payBill": False, "lastChecked": "2026-07-25"},
            "metaAds": {"runningAds": False, "facebookPage": None, "instagramPage": None, "lastSeen": "2026-07-25"},
            "swiggy": {"available": True, "dineout": True},
            "lead": {"score": 0, "priority": "LOW", "assignedTo": None, "exported": False},
        }
    }
