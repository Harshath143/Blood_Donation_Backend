from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.donation import Donation

class DonationRepository(BaseRepository[Donation]):
    def __init__(self, db: AsyncSession):
        super().__init__(Donation, db)

    async def get_by_donor_id(self, donor_id: UUID) -> list[Donation]:
        stmt = select(Donation).where(Donation.donor_id == donor_id).order_by(Donation.donated_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
