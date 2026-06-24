import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from sqlalchemy import (
    String, Boolean, DateTime, Date, 
    Integer, Numeric, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from app.database import Base

class Donor(Base):
    __tablename__ = "donors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        unique=True, nullable=False
    )

    # Blood & identity
    blood_type: Mapped[str] = mapped_column(
        String(5), nullable=False, index=True
    )  # A+, A-, B+, B-, O+, O-, AB+, AB-
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    # Location
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str | None] = mapped_column(String(10))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    # PostGIS geometry point — SRID 4326 = WGS84 (standard GPS)
    location: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=True
    )

    # Availability
    # always | weekends | on_request | unavailable
    availability: Mapped[str] = mapped_column(
        String(20), default="on_request"
    )
    is_available_emergency: Mapped[bool] = mapped_column(
        Boolean, default=True
    )

    # Donation history
    last_donation_date: Mapped[date | None] = mapped_column(Date)
    total_donations: Mapped[int] = mapped_column(Integer, default=0)

    # Medical info
    has_medical_conditions: Mapped[bool] = mapped_column(
        Boolean, default=False
    )
    medical_conditions: Mapped[list] = mapped_column(JSONB, default=list)
    current_medications: Mapped[list] = mapped_column(JSONB, default=list)

    # Status
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="donor_profile")
    matches: Mapped[list["Match"]] = relationship(back_populates="donor")
    donations: Mapped[list["Donation"]] = relationship(back_populates="donor")
