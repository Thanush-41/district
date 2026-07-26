from app.database.mongo import get_restaurants_db
from app.services import recompute_lead_score


def calculate_scores() -> list[dict]:
    db = get_restaurants_db()
    for restaurant in db.values():
        recompute_lead_score(restaurant)
    return list(db.values())
