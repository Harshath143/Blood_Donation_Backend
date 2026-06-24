from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class BloodRequestOut(BaseModel):
    id: UUID
    request_number: str
    requester_id: UUID
    patient_name: str
    patient_age: int | None
    blood_type_needed: str
    units_needed: int
    hospital_id: UUID | None
    hospital_name: str
    city: str
    state: str
    latitude: Decimal | None
    longitude: Decimal | None
    required_by: datetime
    urgency_level: str
    contact_name: str
    contact_phone: str
    status: str
    prescription_oid: int | None
    prescription_name: str | None
    prescription_mime: str | None
    case_description: str | None
    matched_at: datetime | None
    fulfilled_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    broadcast_radius_km: int
    donors_notified: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
