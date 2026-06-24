from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.database import get_db
from app.dependencies import get_current_user, rate_limit_standard
from app.schemas.user import UserOut, UserUpdate
from app.repositories.user_repo import UserRepository
from app.models.user import User

router = APIRouter()

@router.get("/me", response_model=UserOut, dependencies=[Depends(rate_limit_standard)])
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user profile.
    """
    return current_user

@router.put("/me", response_model=UserOut, dependencies=[Depends(rate_limit_standard)])
async def update_me(
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update current user profile.
    """
    user_repo = UserRepository(db)
    
    update_data = body.dict(exclude_unset=True)
    
    # Check for duplicate email/phone if they are changing
    if "email" in update_data and update_data["email"] != current_user.email:
        existing = await user_repo.get_by_email(update_data["email"])
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        # Reset verification status if email changes
        current_user.email_verified = False

    if "phone" in update_data and update_data["phone"] != current_user.phone:
        existing = await user_repo.get_by_phone(update_data["phone"])
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )

    updated_user = await user_repo.update(current_user, update_data)
    await db.commit()
    await db.refresh(updated_user)
    
    return updated_user
