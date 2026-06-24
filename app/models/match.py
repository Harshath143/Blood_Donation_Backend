import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import String, DateTime, Numeric, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("request_id", "donor_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blood_requests.id", ondelete="CASCADE"),
        index=True
    )
    donor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("donors.id"), index=True
    )

    # notified | accepted | rejected | donated | no_response
    status: Mapped[str] = mapped_column(String(20), default="notified")
    distance_km: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    # exact | compatible
    compatibility: Mapped[str | None] = mapped_column(String(10))

    notified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    donated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    request: Mapped["BloodRequest"] = relationship(back_populates="matches")
    donor: Mapped["Donor"] = relationship(back_populates="matches")
