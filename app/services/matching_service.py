from uuid import UUID
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import select, and_, or_, cast, func
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2 import Geography
import structlog
from app.models.match import Match
from app.models.blood_request import BloodRequest
from app.models.donor import Donor
from app.core.constants import COMPATIBLE_DONORS

logger = structlog.get_logger()

URGENCY_NOTIFY_COUNT = {"critical": 15, "urgent": 8, "planned": 3}
URGENCY_CHANNELS     = {
    "critical": ["email", "in_app"],
    "urgent":   ["email", "in_app"],
    "planned":  ["email", "in_app"]
}
SEARCH_RADII_KM = [10, 25, 50, 100]


class MatchingService:

    def __init__(self, db: AsyncSession, ws_manager, notification_service):
        self.db = db
        self.ws_manager = ws_manager
        self.notification_service = notification_service

    async def find_and_notify_donors(self, request_id: UUID) -> dict:
        request = await self.db.get(BloodRequest, request_id)
        if not request:
            return {"found": False, "reason": "request_not_found"}

        compatible_types = COMPATIBLE_DONORS.get(request.blood_type_needed, [])

        # Expand search radius until donors found
        matched_donors = []
        used_radius = 0
        for radius in SEARCH_RADII_KM:
            donors = await self._search_donors(
                blood_types=compatible_types,
                lat=float(request.latitude),
                lng=float(request.longitude),
                radius_km=radius
            )
            if donors:
                matched_donors = donors
                used_radius = radius
                break

        if not matched_donors:
            request.status = "no_match"
            await self.db.commit()
            await self.notification_service.notify_no_match(request)
            return {"found": False, "reason": "no_eligible_donors"}

        # Score and rank
        scored = self._score_donors(matched_donors, request)
        top_n = URGENCY_NOTIFY_COUNT.get(request.urgency_level, 5)
        top_donors = scored[:top_n]

        channels = URGENCY_CHANNELS.get(request.urgency_level, ["in_app"])

        # Create match records + notify
        notified = 0
        for donor, score, distance_km in top_donors:
            compatibility = (
                "exact" if donor.blood_type == request.blood_type_needed
                else "compatible"
            )

            # Avoid duplicate matches
            existing = await self.db.execute(
                select(Match).where(
                    and_(
                        Match.request_id == request_id,
                        Match.donor_id == donor.id
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue

            match = Match(
                request_id=request_id,
                donor_id=donor.id,
                distance_km=distance_km,
                compatibility=compatibility
            )
            self.db.add(match)

            await self.notification_service.notify_donor(
                donor=donor,
                request=request,
                channels=channels
            )
            notified += 1

        # Update request status
        request.status = "matched"
        request.matched_at = datetime.now(timezone.utc)
        request.donors_notified = notified
        request.broadcast_radius_km = used_radius
        await self.db.commit()

        # Real-time update to requester
        await self.ws_manager.send_to_user(
            str(request.requester_id),
            {
                "event": "match_found",
                "request_id": str(request_id),
                "donors_notified": notified,
                "search_radius_km": used_radius
            }
        )

        logger.info(
            "matching_complete",
            request_id=str(request_id),
            donors_notified=notified,
            radius_km=used_radius
        )
        return {"found": True, "notified": notified, "radius_km": used_radius}

    async def _search_donors(
        self,
        blood_types: list[str],
        lat: float,
        lng: float,
        radius_km: float
    ) -> list[Donor]:
        """
        PostGIS ST_DWithin query.
        Only returns donors who are:
        - Active and verified
        - Eligible (last donation >= 56 days ago or never donated)
        - Available (not set to 'unavailable')
        """
        point_wkt = f"SRID=4326;POINT({lng} {lat})"
        radius_m = radius_km * 1000
        eligible_cutoff = date.today() - timedelta(days=56)

        stmt = (
            select(
                Donor,
                func.ST_Distance(
                    cast(Donor.location, Geography),
                    func.ST_GeogFromText(point_wkt)
                ).label("distance_m")
            )
            .where(
                and_(
                    Donor.blood_type.in_(blood_types),
                    Donor.is_active == True,
                    Donor.is_verified == True,
                    Donor.availability != "unavailable",
                    or_(
                        Donor.last_donation_date == None,
                        Donor.last_donation_date <= eligible_cutoff
                    ),
                    func.ST_DWithin(
                        cast(Donor.location, Geography),
                        func.ST_GeogFromText(point_wkt),
                        radius_m
                    )
                )
            )
            .order_by("distance_m")
            .limit(50)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        # Attach distance_km as attribute for scoring
        donors = []
        for donor, distance_m in rows:
            donor.distance_km = round(distance_m / 1000, 2)
            donors.append(donor)
        return donors

    def _score_donors(
        self,
        donors: list[Donor],
        request: BloodRequest
    ) -> list[tuple]:
        """
        Score formula (max 100 points):
        - Exact blood type match:    +40 pts
        - Proximity (max 30 pts):    30 - (distance_km * 0.3)
        - Emergency availability:    +15 pts
        - Availability 'always':     +10 pts
        - Donation count (capped 5): +1 pt each
        """
        scored = []
        for donor in donors:
            score = 0.0

            if donor.blood_type == request.blood_type_needed:
                score += 40
            score += max(0, 30 - (donor.distance_km * 0.3))
            if donor.is_available_emergency:
                score += 15
            if donor.availability == "always":
                score += 10
            score += min(donor.total_donations, 5)

            scored.append((donor, score, donor.distance_km))

        return sorted(scored, key=lambda x: x[1], reverse=True)
