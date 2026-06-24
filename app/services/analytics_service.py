from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.donation import Donation
from app.models.blood_request import BloodRequest
from app.models.donor import Donor

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_statistics(self) -> dict:
        """Returns aggregate platform statistics."""
        # Total donations count
        donations_stmt = select(func.count(Donation.id))
        donations_res = await self.db.execute(donations_stmt)
        total_donations = donations_res.scalar() or 0

        # Total blood requests count
        requests_stmt = select(func.count(BloodRequest.id))
        requests_res = await self.db.execute(requests_stmt)
        total_requests = requests_res.scalar() or 0

        # Fulfilled requests count
        fulfilled_stmt = select(func.count(BloodRequest.id)).where(BloodRequest.status == "fulfilled")
        fulfilled_res = await self.db.execute(fulfilled_stmt)
        fulfilled_requests = fulfilled_res.scalar() or 0

        # Active donors count
        donors_stmt = select(func.count(Donor.id)).where(Donor.is_active == True)
        donors_res = await self.db.execute(donors_stmt)
        active_donors = donors_res.scalar() or 0

        return {
            "total_donations": total_donations,
            "total_requests": total_requests,
            "fulfilled_requests": fulfilled_requests,
            "active_donors": active_donors,
            "fulfillment_rate": round((fulfilled_requests / total_requests) * 100, 2) if total_requests > 0 else 0.0
        }
