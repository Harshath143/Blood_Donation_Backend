import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import String, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Donation(Base):
    __tablename__ = "donations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    donor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("donors.id"), index=True
    )
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blood_requests.id"), nullable=True
    )
    blood_bank_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blood_banks.id"), nullable=True
    )

    blood_type: Mapped[str] = mapped_column(String(5), nullable=False)
    units_donated: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=1.0)
    # whole_blood | platelets | plasma | double_red
    donation_type: Mapped[str] = mapped_column(String(20), default="whole_blood")

    donated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    location_name: Mapped[str | None] = mapped_column(String(255))

    # Certificate
    certificate_number: Mapped[str | None] = mapped_column(
        String(50), unique=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    donor: Mapped["Donor"] = relationship(back_populates="donations")
