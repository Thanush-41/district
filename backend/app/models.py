from typing import List, Optional
from pydantic import BaseModel, Field


class DistrictCheckPayload(BaseModel):
    restaurant_id: str
    onboarded: bool = False
    pay_bill: bool = False


class MetaUpdatePayload(BaseModel):
    restaurant_id: str
    running_ads: bool = False
    facebook_page: Optional[str] = None
    instagram_page: Optional[str] = None


class AssignLeadsPayload(BaseModel):
    restaurant_ids: List[str]
    assigned_to: Optional[str] = None


class ZomatoUpdatePayload(BaseModel):
    restaurant_id: str
    listed: bool = False


class NearbySearchPayload(BaseModel):
    place: str
    radius_km: float = 60
    keywords: Optional[List[str]] = None


class FlagUpdatePayload(BaseModel):
    read: Optional[bool] = None
    important: Optional[bool] = None
    saved: Optional[bool] = None


class Restaurant(BaseModel):
    _id: str
    google: dict
    district: dict
    metaAds: dict
    swiggy: dict
    lead: dict
