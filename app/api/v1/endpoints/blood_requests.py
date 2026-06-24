from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile, Query, Response, Body
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, and_, or_

from app.database import get_db
from app.dependencies import get_current_user, get_redis, rate_limit_standard
from app.schemas.blood_request import BloodRequestOut
from app.schemas.match import MatchOut, MatchResponse
from app.services.request_service import BloodRequestService
from app.services.geolocation_service import GeolocationService
from app.repositories.request_repo import BloodRequestRepository
from app.repositories.donor_repo import DonorRepository
from app.repositories.match_repo import MatchRepository
from app.models.user import User
from app.models.blood_request import BloodRequest
from app.models.match import Match
from app.websocket.manager import ws_manager
from app.integrations.storage import retrieve_prescription

import structlog

logger = structlog.get_logger()
router = APIRouter()

@router.post("", response_model=BloodRequestOut, dependencies=[Depends(rate_limit_standard)])
async def create_request(
    patient_name: str = Form(...),
    patient_age: int = Form(None),
    blood_type_needed: str = Form(...),
    units_needed: int = Form(...),
    hospital_name: str = Form(...),
    hospital_address: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    required_by: datetime = Form(...),
    urgency_level: str = Form(...),
    contact_name: str = Form(...),
    contact_phone: str = Form(...),
    case_description: str | None = Form(None),
    prescription: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user)
):
    """
    Submit a new blood request, geocode the hospital, and trigger the matching process in the background.
    """
    geo_service = GeolocationService(redis)
    request_service = BloodRequestService(db, geo_service)
    
    request = await request_service.create_request(
        requester_id=str(current_user.id),
        patient_name=patient_name,
        patient_age=patient_age,
        blood_type_needed=blood_type_needed,
        units_needed=units_needed,
        hospital_name=hospital_name,
        hospital_address=hospital_address,
        city=city,
        state=state,
        required_by=required_by,
        urgency_level=urgency_level,
        contact_name=contact_name,
        contact_phone=contact_phone,
        case_description=case_description,
        prescription_file=prescription
    )
    
    await db.commit()
    await db.refresh(request)
    return request

@router.get("", response_model=list[BloodRequestOut], dependencies=[Depends(rate_limit_standard)])
async def list_requests(
    status: str | None = Query(None),
    blood_type: str | None = Query(None),
    city: str | None = Query(None),
    my_requests: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List and filter blood requests.
    """
    stmt = select(BloodRequest)
    filters = []

    if my_requests:
        filters.append(BloodRequest.requester_id == current_user.id)
    if status:
        filters.append(BloodRequest.status == status)
    if blood_type:
        filters.append(BloodRequest.blood_type_needed == blood_type)
    if city:
        filters.append(BloodRequest.city.ilike(f"%{city}%"))

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.order_by(BloodRequest.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())

@router.get("/{request_id}", response_model=BloodRequestOut, dependencies=[Depends(rate_limit_standard)])
async def get_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single blood request by ID.
    """
    request = await db.get(BloodRequest, request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blood request not found"
        )
    return request

@router.get("/{request_id}/prescription", dependencies=[Depends(rate_limit_standard)])
async def download_prescription(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download/retrieve the uploaded medical certificate (prescription) from Large Objects.
    """
    request = await db.get(BloodRequest, request_id)
    if not request or not request.prescription_oid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found or not uploaded"
        )

    try:
        file_bytes = retrieve_prescription(request.prescription_oid)
    except Exception as e:
        logger.error("prescription_download_error", request_id=str(request_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve prescription"
        )

    return Response(
        content=file_bytes,
        media_type=request.prescription_mime or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{request.prescription_name or "prescription"}"'
        }
    )

@router.put("/{request_id}/cancel", response_model=BloodRequestOut, dependencies=[Depends(rate_limit_standard)])
async def cancel_request(
    request_id: UUID,
    cancellation_reason: str = Body(None, embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel an active blood request.
    Only the creator or super_admin can cancel it.
    """
    request = await db.get(BloodRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.requester_id != current_user.id and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Not authorized to cancel this request")

    request.status = "cancelled"
    request.cancelled_at = datetime.now(timezone.utc)
    request.cancellation_reason = cancellation_reason

    await db.commit()
    await db.refresh(request)
    return request

@router.put("/{request_id}/fulfill", response_model=BloodRequestOut, dependencies=[Depends(rate_limit_standard)])
async def fulfill_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a blood request as fulfilled.
    Only the creator or super_admin can fulfill it.
    """
    request = await db.get(BloodRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.requester_id != current_user.id and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Not authorized to update this request")

    request.status = "fulfilled"
    request.fulfilled_at = datetime.now(timezone.utc)

    # Mark associated matches as donated/complete if they were accepted
    stmt = select(Match).where(and_(Match.request_id == request_id, Match.status == "accepted"))
    result = await db.execute(stmt)
    accepted_matches = result.scalars().all()
    for match in accepted_matches:
        match.status = "donated"
        match.donated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(request)
    return request

@router.get("/{request_id}/matches", response_model=list[MatchOut], dependencies=[Depends(rate_limit_standard)])
async def get_request_matches(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all matches (candidates notified) for a specific request.
    Only accessible by the request owner, the matched donors, or admins.
    """
    request = await db.get(BloodRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    is_admin = current_user.role in ["super_admin", "hospital_admin"]
    is_owner = request.requester_id == current_user.id
    
    donor_repo = DonorRepository(db)
    donor = await donor_repo.get_by_user_id(current_user.id)
    
    match_repo = MatchRepository(db)
    matches = await match_repo.get_matches_for_request(request_id)
    
    is_matched_donor = any(donor and m.donor_id == donor.id for m in matches)

    if not (is_admin or is_owner or is_matched_donor):
        raise HTTPException(status_code=403, detail="Not authorized to view matches for this request")

    # If the user is a donor, filter to show only their match record
    if is_matched_donor and not (is_admin or is_owner):
        matches = [m for m in matches if donor and m.donor_id == donor.id]

    return matches

@router.post("/{request_id}/matches/respond", response_model=MatchOut, dependencies=[Depends(rate_limit_standard)])
async def respond_to_match(
    request_id: UUID,
    body: MatchResponse,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accept or reject a blood request notification.
    Must be called by the notified donor.
    """
    donor_repo = DonorRepository(db)
    donor = await donor_repo.get_by_user_id(current_user.id)
    if not donor:
        raise HTTPException(status_code=404, detail="Donor profile not found")

    match_repo = MatchRepository(db)
    match = await match_repo.get_by_request_and_donor(request_id, donor.id)
    if not match:
        raise HTTPException(status_code=404, detail="No matching alert found for this donor/request combination")

    match.status = body.status
    match.responded_at = datetime.now(timezone.utc)
    if body.status == "rejected":
        match.rejection_reason = body.rejection_reason
        
    await db.commit()
    await db.refresh(match)

    # Load request details to send WS updates
    request = await db.get(BloodRequest, request_id)
    if request:
        event_name = "match_accepted" if body.status == "accepted" else "match_declined"
        await ws_manager.send_to_user(
            str(request.requester_id),
            {
                "event": event_name,
                "request_id": str(request_id),
                "donor_name": current_user.full_name,
                "donor_phone": current_user.phone if body.status == "accepted" else None
            }
        )

    return match
