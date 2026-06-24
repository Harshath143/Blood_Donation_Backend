from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.blood_bank import BloodBank, BloodInventory

class BloodBankRepository(BaseRepository[BloodBank]):
    def __init__(self, db: AsyncSession):
        super().__init__(BloodBank, db)

    async def get_inventory(self, blood_bank_id: str) -> list[BloodInventory]:
        stmt = select(BloodInventory).where(BloodInventory.blood_bank_id == blood_bank_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_inventory_by_type(self, blood_bank_id: str, blood_type: str) -> BloodInventory | None:
        stmt = select(BloodInventory).where(
            and_(
                BloodInventory.blood_bank_id == blood_bank_id,
                BloodInventory.blood_type == blood_type
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
