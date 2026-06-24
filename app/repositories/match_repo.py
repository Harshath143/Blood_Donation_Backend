from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.match import Match

class MatchRepository(BaseRepository[Match]):
    def __init__(self, db: AsyncSession):
        super().__init__(Match, db)

    async def get_by_request_and_donor(self, request_id: UUID, donor_id: UUID) -> Match | None:
        stmt = select(Match).where(
            and_(
                Match.request_id == request_id,
                Match.donor_id == donor_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_matches_for_request(self, request_id: UUID) -> list[Match]:
        stmt = select(Match).where(Match.request_id == request_id).order_by(Match.distance_km.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
