from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, rate_limit_standard
from app.schemas.donation import DonationCreate, DonationOut
from app.repositories.donation_repo import DonationRepository
from app.repositories.donor_repo import DonorRepository
from app.models.donation import Donation
from app.models.donor import Donor
from app.models.user import User

router = APIRouter()

@router.post("", response_model=DonationOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit_standard)])
async def record_donation(
    body: DonationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Record a new blood donation.
    If donor_id is not specified, it records it for the current user's donor profile.
    Automatically updates the donor's last_donation_date and increments total_donations count.
    """
    donor_repo = DonorRepository(db)
    
    # 1. Resolve donor ID
    if body.donor_id:
        # Check permissions: recording for others requires admin/hospital role
        if current_user.role not in ["super_admin", "hospital_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only staff or administrators can record donations for other donors."
            )
        donor = await db.get(Donor, body.donor_id)
    else:
        # Self-recording
        donor = await donor_repo.get_by_user_id(current_user.id)

    if not donor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donor profile not found."
        )

    # 2. Check if a donation certificate number already exists (must be unique if provided)
    if body.certificate_number:
        stmt = select(Donation).where(Donation.certificate_number == body.certificate_number)
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A donation with this certificate number has already been recorded."
            )

    # 3. Create Donation
    donation = Donation(
        donor_id=donor.id,
        request_id=body.request_id,
        blood_bank_id=body.blood_bank_id,
        blood_type=body.blood_type,
        units_donated=body.units_donated,
        donation_type=body.donation_type,
        donated_at=body.donated_at,
        location_name=body.location_name,
        certificate_number=body.certificate_number
    )
    db.add(donation)

    # 4. Update Donor Profile statistics
    # Only update donor last_donation_date if this donation is newer than the current value
    donation_date = body.donated_at.date()
    if not donor.last_donation_date or donation_date > donor.last_donation_date:
        donor.last_donation_date = donation_date
        
    donor.total_donations += 1
    
    await db.commit()
    await db.refresh(donation)
    return donation

@router.get("/me", response_model=list[DonationOut], dependencies=[Depends(rate_limit_standard)])
async def get_my_donations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the donation history of the current authenticated user.
    """
    donor_repo = DonorRepository(db)
    donor = await donor_repo.get_by_user_id(current_user.id)
    if not donor:
        return []

    donation_repo = DonationRepository(db)
    return await donation_repo.get_by_donor_id(donor.id)

@router.get("/donor/{donor_id}", response_model=list[DonationOut], dependencies=[Depends(rate_limit_standard)])
async def get_donor_donations(
    donor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the donation history of a specific donor (admin or hospital staff only).
    """
    if current_user.role not in ["super_admin", "hospital_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    donation_repo = DonationRepository(db)
    return await donation_repo.get_by_donor_id(donor_id)
