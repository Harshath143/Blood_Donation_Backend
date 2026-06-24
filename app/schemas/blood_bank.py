from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class BloodInventoryOut(BaseModel):
    id: UUID
    blood_bank_id: UUID
    blood_type: str
    units_available: int
    units_reserved: int
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)

class BloodBankOut(BaseModel):
    id: UUID
    name: str
    hospital_id: UUID | None
    address: str
    city: str
    state: str
    pincode: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    phone: str | None
    email: str | None
    operating_hours: dict
    is_24x7: bool
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class BloodBankCreate(BaseModel):
    name: str
    hospital_id: UUID | None = None
    address: str
    city: str
    state: str
    pincode: str | None = None
    phone: str | None = None
    email: str | None = None
    operating_hours: dict = {}
    is_24x7: bool = False

class InventoryUpdate(BaseModel):
    blood_type: str
    units: int

