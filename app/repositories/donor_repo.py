from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.donor import Donor

class DonorRepository(BaseRepository[Donor]):
    def __init__(self, db: AsyncSession):
        super().__init__(Donor, db)

    async def get_by_user_id(self, user_id: UUID) -> Donor | None:
        stmt = select(Donor).where(and_(Donor.user_id == user_id, Donor.is_active == True))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
