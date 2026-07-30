from typing import Dict, Optional

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.config import settings
from app.seed import seed_restaurants

MONGO_URI = settings.mongo_uri
MONGO_DB_NAME = settings.mongo_db_name

_client: Optional[MongoClient] = None
_collection_name = "restaurants"


_in_memory_store: Dict[str, dict] = seed_restaurants()


def get_client() -> Optional[MongoClient]:
    global _client
    if _client is not None:
        return _client
    if not MONGO_URI:
        return None
    try:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        _client.admin.command("ping")
    except PyMongoError:
        _client = None
    return _client


def _ensure_seed_in_mongo(collection) -> None:
    if collection.count_documents({}) == 0:
        seed = seed_restaurants()
        if seed:
            collection.insert_many(list(seed.values()))


def get_restaurants_db() -> Dict[str, dict]:
    client = get_client()
    if client is None:
        if not _in_memory_store:
            _in_memory_store.update(seed_restaurants())
        return _in_memory_store

    db = client[MONGO_DB_NAME]
    collection = db[_collection_name]
    _ensure_seed_in_mongo(collection)

    documents = list(collection.find({}))
    _in_memory_store.clear()
    for document in documents:
        document_id = str(document.get("_id"))
        document["_id"] = document_id
        _in_memory_store[document_id] = document
    return _in_memory_store


def save_restaurant(restaurant: dict) -> dict:
    restaurant_id = restaurant.get("_id")
    if restaurant_id is None:
        restaurant_id = restaurant.get("google", {}).get("placeId", "restaurant")
    restaurant["_id"] = restaurant_id
    _in_memory_store[restaurant_id] = restaurant

    client = get_client()
    if client is None:
        return restaurant

    db = client[MONGO_DB_NAME]
    collection = db[_collection_name]
    collection.update_one({"_id": restaurant_id}, {"$set": restaurant}, upsert=True)
    return restaurant


def list_restaurants_from_store() -> list[dict]:
    client = get_client()
    if client is None:
        return list(_in_memory_store.values())

    db = client[MONGO_DB_NAME]
    collection = db[_collection_name]
    return list(collection.find({}))


def load_seed_if_needed() -> None:
    client = get_client()
    if client is not None:
        db = client[MONGO_DB_NAME]
        collection = db[_collection_name]
        _ensure_seed_in_mongo(collection)
        return

    if not _in_memory_store:
        _in_memory_store.update(seed_restaurants())


def reset_store() -> None:
    _in_memory_store.clear()
    _in_memory_store.update(seed_restaurants())

    client = get_client()
    if client is None:
        return

    db = client[MONGO_DB_NAME]
    collection = db[_collection_name]
    collection.delete_many({})
    collection.insert_many(list(_in_memory_store.values()))
