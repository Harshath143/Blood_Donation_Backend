from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class DonationOut(BaseModel):
    id: UUID
    donor_id: UUID
    request_id: UUID | None
    blood_bank_id: UUID | None
    blood_type: str
    units_donated: Decimal
    donation_type: str
    donated_at: datetime
    location_name: str | None
    certificate_number: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DonationCreate(BaseModel):
    donor_id: UUID | None = None
    request_id: UUID | None = None
    blood_bank_id: UUID | None = None
    blood_type: str
    units_donated: Decimal = Decimal("1.0")
    donation_type: str = "whole_blood"
    donated_at: datetime
    location_name: str | None = None
    certificate_number: str | None = None

