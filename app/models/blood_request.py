import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    String, Boolean, DateTime, Integer,
    Numeric, Text, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from app.database import Base

class BloodRequest(Base):
    __tablename__ = "blood_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )  # LD-XXXXXX format
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Patient info
    patient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    patient_age: Mapped[int | None] = mapped_column(Integer)
    blood_type_needed: Mapped[str] = mapped_column(
        String(5), nullable=False, index=True
    )
    units_needed: Mapped[int] = mapped_column(Integer, nullable=False)

    # Hospital
    hospital_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=True
    )
    hospital_name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    location: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=True
    )

    # Timing
    required_by: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    # critical | urgent | planned
    urgency_level: Mapped[str] = mapped_column(
        String(10), default="urgent", index=True
    )

    # Contact
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)

    # Status: searching | matched | fulfilled | cancelled | expired | no_match
    status: Mapped[str] = mapped_column(
        String(20), default="searching", index=True
    )

    # Prescription (PostgreSQL large object)
    prescription_oid: Mapped[int | None] = mapped_column(Integer)
    prescription_name: Mapped[str | None] = mapped_column(String(255))
    prescription_mime: Mapped[str | None] = mapped_column(String(50))

    # Case
    case_description: Mapped[str | None] = mapped_column(Text)

    # Tracking
    matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_reason: Mapped[str | None] = mapped_column(Text)

    # Broadcast tracking
    broadcast_radius_km: Mapped[int] = mapped_column(Integer, default=25)
    donors_notified: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    matches: Mapped[list["Match"]] = relationship(back_populates="request")
