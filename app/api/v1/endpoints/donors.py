from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.database import get_db
from app.dependencies import get_current_user, get_redis, rate_limit_standard
from app.schemas.donor import DonorCreate, DonorOut, DonorAvailabilityUpdate
from app.services.donor_service import DonorService
from app.services.geolocation_service import GeolocationService
from app.repositories.donor_repo import DonorRepository
from app.models.user import User

router = APIRouter()

@router.post("/profile", response_model=DonorOut, dependencies=[Depends(rate_limit_standard)])
async def create_or_update_profile(
    body: DonorCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user)
):
    """
    Create or update current user's donor profile.
    Automatically geocodes the address using Nominatim + Redis cache.
    Also upgrades user role to 'donor' if they were not already.
    """
    geo_service = GeolocationService(redis)
    donor_service = DonorService(db, geo_service)
    
    # 1. Update/Create donor profile
    donor = await donor_service.create_or_update_profile(
        user_id=current_user.id,
        blood_type=body.blood_type,
        date_of_birth=body.date_of_birth,
        gender=body.gender,
        weight_kg=body.weight_kg,
        city=body.city,
        state=body.state,
        pincode=body.pincode,
        address=body.address
    )
    
    # 2. Update user role if it's not donor (unless they are admin)
    if current_user.role not in ["donor", "super_admin", "hospital_admin"]:
        current_user.role = "donor"
        db.add(current_user)
        
    await db.commit()
    await db.refresh(donor)
    return donor

@router.get("/me", response_model=DonorOut, dependencies=[Depends(rate_limit_standard)])
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's donor profile.
    """
    donor_repo = DonorRepository(db)
    donor = await donor_repo.get_by_user_id(current_user.id)
    if not donor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donor profile not found for this user."
        )
    return donor

@router.put("/availability", response_model=DonorOut, dependencies=[Depends(rate_limit_standard)])
async def update_availability(
    body: DonorAvailabilityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update donor availability status and emergency availability switch.
    """
    donor_repo = DonorRepository(db)
    donor = await donor_repo.get_by_user_id(current_user.id)
    if not donor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donor profile not found. Please create a donor profile first."
        )
    
    donor.availability = body.availability
    donor.is_available_emergency = body.is_available_emergency
    
    await db.commit()
    await db.refresh(donor)
    return donor
