from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

class DonorCreate(BaseModel):
    blood_type: str = Field(..., max_length=5)
    date_of_birth: date
    gender: str = Field(..., max_length=10)
    weight_kg: float
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    pincode: str | None = Field(None, max_length=10)
    address: str

class DonorOut(BaseModel):
    id: UUID
    user_id: UUID
    blood_type: str
    date_of_birth: date
    gender: str
    weight_kg: Decimal
    city: str
    state: str
    pincode: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    availability: str
    is_available_emergency: bool
    last_donation_date: date | None
    total_donations: int
    has_medical_conditions: bool
    is_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DonorAvailabilityUpdate(BaseModel):
    availability: str = Field(..., max_length=20)
    is_available_emergency: bool

