import secrets
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.elements import WKTElement
from fastapi import HTTPException, status, UploadFile
from app.repositories.request_repo import BloodRequestRepository
from app.services.geolocation_service import GeolocationService
from app.models.blood_request import BloodRequest
from app.integrations.storage import store_prescription

class BloodRequestService:
    def __init__(self, db: AsyncSession, geolocation_service: GeolocationService):
        self.db = db
        self.repo = BloodRequestRepository(db)
        self.geo_service = geolocation_service

    async def create_request(
        self,
        requester_id: str,
        patient_name: str,
        patient_age: int,
        blood_type_needed: str,
        units_needed: int,
        hospital_name: str,
        hospital_address: str,
        city: str,
        state: str,
        required_by: datetime,
        urgency_level: str,
        contact_name: str,
        contact_phone: str,
        case_description: str | None,
        prescription_file: UploadFile | None = None
    ) -> BloodRequest:
        """Creates a blood request, geocodes the hospital address, stores prescription attachment, and registers the task."""
        # 1. Generate unique request number
        req_num = f"LD-{secrets.randbelow(900000) + 100000}"
        
        # 2. Geocode location details
        lat, lon = await self.geo_service.get_coordinates(hospital_address, city, state)
        if not lat or not lon:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not geocode hospital address."
            )

        location_element = WKTElement(f"POINT({lon} {lat})", srid=4326)

        # 3. Store prescription large object if uploaded
        pres_oid = None
        pres_name = None
        pres_mime = None
        
        if prescription_file:
            content = await prescription_file.read()
            pres_name = prescription_file.filename
            pres_mime = prescription_file.content_type or "application/pdf"
            try:
                # store_prescription is a sync function calling psycopg2
                pres_oid = store_prescription(content, pres_name, pres_mime)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Prescription file upload failed: {str(e)}"
                )

        new_request = BloodRequest(
            request_number=req_num,
            requester_id=requester_id,
            patient_name=patient_name,
            patient_age=patient_age,
            blood_type_needed=blood_type_needed,
            units_needed=units_needed,
            hospital_name=hospital_name,
            city=city,
            state=state,
            latitude=Decimal(str(lat)),
            longitude=Decimal(str(lon)),
            location=location_element,
            required_by=required_by,
            urgency_level=urgency_level,
            contact_name=contact_name,
            contact_phone=contact_phone,
            status="searching",
            prescription_oid=pres_oid,
            prescription_name=pres_name,
            prescription_mime=pres_mime,
            case_description=case_description,
            broadcast_radius_km=25,
            donors_notified=0
        )
        
        request = await self.repo.create(new_request)
        await self.db.flush()

        # Enqueue background matching Celery task
        from app.tasks.matching_tasks import trigger_matching_task
        trigger_matching_task.delay(str(request.id))

        return request
