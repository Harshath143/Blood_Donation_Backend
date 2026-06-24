from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from uuid import UUID
from decimal import Decimal
from sqlalchemy import select, and_
from geoalchemy2.elements import WKTElement

from app.database import get_db
from app.dependencies import get_current_user, get_redis, RoleChecker, rate_limit_standard
from app.schemas.blood_bank import BloodBankOut, BloodBankCreate, BloodInventoryOut, InventoryUpdate
from app.services.blood_bank_service import BloodBankService
from app.services.geolocation_service import GeolocationService
from app.repositories.blood_bank_repo import BloodBankRepository
from app.models.blood_bank import BloodBank, BloodInventory
from app.models.user import User

router = APIRouter()

@router.post("", response_model=BloodBankOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit_standard), Depends(RoleChecker(["super_admin"]))])
async def create_blood_bank(
    body: BloodBankCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Create a new blood bank. Geocodes the address in the background.
    Only accessible by super_admin.
    """
    geo_service = GeolocationService(redis)
    lat, lon = await geo_service.get_coordinates(body.address, body.city, body.state)
    
    location_element = None
    if lat and lon:
        location_element = WKTElement(f"POINT({lon} {lat})", srid=4326)

    blood_bank = BloodBank(
        name=body.name,
        hospital_id=body.hospital_id,
        address=body.address,
        city=body.city,
        state=body.state,
        pincode=body.pincode,
        latitude=Decimal(str(lat)) if lat else None,
        longitude=Decimal(str(lon)) if lon else None,
        location=location_element,
        phone=body.phone,
        email=body.email,
        operating_hours=body.operating_hours,
        is_24x7=body.is_24x7,
        is_active=True,
        is_verified=True
    )
    
    db.add(blood_bank)
    await db.commit()
    await db.refresh(blood_bank)
    return blood_bank

@router.get("", response_model=list[BloodBankOut], dependencies=[Depends(rate_limit_standard)])
async def list_blood_banks(
    city: str | None = Query(None),
    state: str | None = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    List and filter blood banks by city or state.
    """
    stmt = select(BloodBank).where(BloodBank.is_active == True)
    filters = []
    if city:
        filters.append(BloodBank.city.ilike(f"%{city}%"))
    if state:
        filters.append(BloodBank.state.ilike(f"%{state}%"))
        
    if filters:
        stmt = stmt.where(and_(*filters))

    result = await db.execute(stmt)
    return list(result.scalars().all())

@router.get("/{blood_bank_id}", response_model=BloodBankOut, dependencies=[Depends(rate_limit_standard)])
async def get_blood_bank(
    blood_bank_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve details of a specific blood bank.
    """
    blood_bank = await db.get(BloodBank, blood_bank_id)
    if not blood_bank or not blood_bank.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blood bank not found"
        )
    return blood_bank

@router.get("/{blood_bank_id}/inventory", response_model=list[BloodInventoryOut], dependencies=[Depends(rate_limit_standard)])
async def get_blood_bank_inventory(
    blood_bank_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the available inventory of blood units at a blood bank.
    """
    repo = BloodBankRepository(db)
    inventory = await repo.get_inventory(str(blood_bank_id))
    return inventory

@router.post("/{blood_bank_id}/inventory", response_model=BloodInventoryOut, dependencies=[Depends(rate_limit_standard), Depends(RoleChecker(["super_admin", "hospital_admin"]))])
async def update_blood_bank_inventory(
    blood_bank_id: UUID,
    body: InventoryUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update (add or subtract) blood units in the inventory of a blood bank.
    Only accessible by super_admin and hospital_admin.
    """
    # Check if blood bank exists
    blood_bank = await db.get(BloodBank, blood_bank_id)
    if not blood_bank:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blood bank not found"
        )

    service = BloodBankService(db)
    inventory = await service.update_inventory(
        blood_bank_id=blood_bank_id,
        blood_type=body.blood_type,
        units=body.units
    )
    
    await db.commit()
    await db.refresh(inventory)
    return inventory
