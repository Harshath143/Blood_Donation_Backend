from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class MatchOut(BaseModel):
    id: UUID
    request_id: UUID
    donor_id: UUID
    status: str
    distance_km: Decimal | None
    compatibility: str | None
    notified_at: datetime
    responded_at: datetime | None
    donated_at: datetime | None
    rejection_reason: str | None

    model_config = ConfigDict(from_attributes=True)

class MatchResponse(BaseModel):
    status: str
    rejection_reason: str | None = None
