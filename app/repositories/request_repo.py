from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.blood_request import BloodRequest

class BloodRequestRepository(BaseRepository[BloodRequest]):
    def __init__(self, db: AsyncSession):
        super().__init__(BloodRequest, db)

    async def get_by_request_number(self, request_number: str) -> BloodRequest | None:
        stmt = select(BloodRequest).where(BloodRequest.request_number == request_number)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
