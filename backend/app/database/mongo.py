import os
from typing import Dict, Optional

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.seed import seed_restaurants

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "district")

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


def get_restaurants_db() -> Dict[str, dict]:
    if not _in_memory_store:
        load_seed_if_needed()

    client = get_client()
    if client is None:
        return _in_memory_store

    db = client[MONGO_DB_NAME]
    collection = db[_collection_name]
    documents = list(collection.find({}))
    if not documents:
        return _in_memory_store

    for document in documents:
        document_id = str(document.get("_id"))
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
    if _in_memory_store:
        return

    _in_memory_store.update(seed_restaurants())

    client = get_client()
    if client is None:
        return

    db = client[MONGO_DB_NAME]
    collection = db[_collection_name]
    if collection.count_documents({}) == 0:
        for restaurant in _in_memory_store.values():
            collection.insert_one(restaurant)


def reset_store() -> None:
    _in_memory_store.clear()
    _in_memory_store.update(seed_restaurants())
