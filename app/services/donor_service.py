from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.elements import WKTElement
from fastapi import HTTPException, status
from app.repositories.donor_repo import DonorRepository
from app.services.geolocation_service import GeolocationService
from app.models.donor import Donor

class DonorService:
    def __init__(self, db: AsyncSession, geolocation_service: GeolocationService):
        self.db = db
        self.repo = DonorRepository(db)
        self.geo_service = geolocation_service

    async def create_or_update_profile(
        self,
        user_id: str,
        blood_type: str,
        date_of_birth: date,
        gender: str,
        weight_kg: float,
        city: str,
        state: str,
        pincode: str | None,
        address: str
    ) -> Donor:
        """Creates or updates a donor profile, geocoding coordinates on save."""
        # 1. Geocode location details
        lat, lon = await self.geo_service.get_coordinates(address, city, state)
        if not lat or not lon:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not geocode the address. Please check address details."
            )

        location_element = WKTElement(f"POINT({lon} {lat})", srid=4326)

        donor = await self.repo.get_by_user_id(user_id)
        if donor:
            # Update profile
            donor.blood_type = blood_type
            donor.date_of_birth = date_of_birth
            donor.gender = gender
            donor.weight_kg = Decimal(str(weight_kg))
            donor.city = city
            donor.state = state
            donor.pincode = pincode
            donor.latitude = Decimal(str(lat))
            donor.longitude = Decimal(str(lon))
            donor.location = location_element
        else:
            # Create new profile
            donor = Donor(
                user_id=user_id,
                blood_type=blood_type,
                date_of_birth=date_of_birth,
                gender=gender,
                weight_kg=Decimal(str(weight_kg)),
                city=city,
                state=state,
                pincode=pincode,
                latitude=Decimal(str(lat)),
                longitude=Decimal(str(lon)),
                location=location_element,
                availability="on_request",
                is_available_emergency=True,
                is_verified=True,  # Default verified for demo simplicity
                is_active=True
            )
            donor = await self.repo.create(donor)
        
        await self.db.flush()
        return donor
