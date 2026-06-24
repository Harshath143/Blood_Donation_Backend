from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.blood_bank_repo import BloodBankRepository
from app.models.blood_bank import BloodInventory

class BloodBankService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BloodBankRepository(db)

    async def update_inventory(self, blood_bank_id: UUID, blood_type: str, units: int) -> BloodInventory:
        """Adds or updates available blood units in inventory."""
        inventory = await self.repo.get_inventory_by_type(str(blood_bank_id), blood_type)
        if not inventory:
            inventory = BloodInventory(
                blood_bank_id=blood_bank_id,
                blood_type=blood_type,
                units_available=units,
                units_reserved=0,
                last_updated=datetime.now(timezone.utc)
            )
            self.db.add(inventory)
        else:
            inventory.units_available += units
            inventory.last_updated = datetime.now(timezone.utc)
        await self.db.flush()
        return inventory

    async def reserve_blood(self, blood_bank_id: UUID, blood_type: str, units: int) -> bool:
        """Reserves blood units, moving them from available to reserved."""
        inventory = await self.repo.get_inventory_by_type(str(blood_bank_id), blood_type)
        if not inventory or inventory.units_available < units:
            return False
        
        inventory.units_available -= units
        inventory.units_reserved += units
        inventory.last_updated = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    async def release_reserved_blood(self, blood_bank_id: UUID, blood_type: str, units: int) -> bool:
        """Releases reserved units (either consumed or returned)."""
        inventory = await self.repo.get_inventory_by_type(str(blood_bank_id), blood_type)
        if not inventory or inventory.units_reserved < units:
            return False

        inventory.units_reserved -= units
        inventory.last_updated = datetime.now(timezone.utc)
        await self.db.flush()
        return True
