from typing import Optional
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


class Restaurant(BaseModel):
    _id: str
    google: dict
    district: dict
    metaAds: dict
    swiggy: dict
    lead: dict
