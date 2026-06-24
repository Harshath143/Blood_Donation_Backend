from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

from app.database import get_db
from app.dependencies import get_redis, rate_limit_auth
from app.schemas.auth import (
    UserRegister, UserLogin, TokenResponse, VerifyOTP,
    TokenRefreshRequest, ForgotPasswordRequest, ResetPasswordRequest
)
from app.schemas.user import UserOut
from app.services.auth_service import AuthService
from app.core.security import (
    send_email_otp, verify_email_otp, verify_token,
    create_access_token, create_refresh_token, blacklist_token,
    hash_password
)
from app.models.user import User
from app.config import get_settings
from app.integrations.email import send_email

import secrets
import hashlib
import structlog

logger = structlog.get_logger()
settings = get_settings()

router = APIRouter()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit_auth)])
async def register(
    body: UserRegister,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Register a new user and send an email verification OTP.
    """
    auth_service = AuthService(db, redis)
    user = await auth_service.register_user(
        email=body.email,
        phone=body.phone,
        password=body.password,
        full_name=body.full_name,
        role=body.role
    )
    await db.commit()
    await db.refresh(user)

    # Send verification email OTP
    try:
        await send_email_otp(str(user.id), user.email, redis)
    except Exception as e:
        logger.error("register_otp_failed", user_id=str(user.id), error=str(e))

    return user

@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit_auth)])
async def login(
    body: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Authenticate a user and return access/refresh tokens.
    Enforces IP-based login throttling and locking.
    """
    ip_address = request.client.host if request.client else "unknown"
    auth_service = AuthService(db, redis)
    
    # This method checks locking, verifies password, and updates last login
    result = await auth_service.authenticate_user(
        email=body.email,
        password=body.password,
        ip_address=ip_address
    )
    await db.commit()
    return result

@router.post("/verify-otp", dependencies=[Depends(rate_limit_auth)])
async def verify_otp(
    body: VerifyOTP,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Verify email OTP. If successful, marks the user's email as verified.
    """
    # Find user by email
    auth_service = AuthService(db, redis)
    user = await auth_service.repo.get_by_email(body.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.email_verified:
        return {"message": "Email is already verified"}

    is_valid = await verify_email_otp(str(user.id), body.otp, redis)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )

    user.email_verified = True
    await db.commit()

    # Send welcome email now that they verified
    try:
        from app.integrations.email import send_welcome_email
        await send_welcome_email(user.email, user.full_name)
    except Exception as e:
        logger.error("welcome_email_failed", user_id=str(user.id), error=str(e))

    return {"message": "Email verified successfully"}

@router.post("/resend-otp", dependencies=[Depends(rate_limit_auth)])
async def resend_otp(
    body: ForgotPasswordRequest,  # Reuse to get email
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Resend verification OTP.
    """
    auth_service = AuthService(db, redis)
    user = await auth_service.repo.get_by_email(body.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.email_verified:
        return {"message": "Email is already verified"}

    # Limit OTP resend rate per user to avoid spam
    resend_key = f"otp_resend_lock:{user.id}"
    if await redis.exists(resend_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait 1 minute before requesting another OTP."
        )

    await send_email_otp(str(user.id), user.email, redis)
    await redis.set(resend_key, "1", ex=60)

    return {"message": "OTP sent successfully"}

@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(rate_limit_auth)])
async def refresh(
    body: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Get a new pair of access/refresh tokens using a valid refresh token.
    Blacklists the old refresh token to prevent replay attacks.
    """
    try:
        payload = await verify_token(body.refresh_token, redis)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )

    user_id = payload.get("sub")
    old_jti = payload.get("jti")
    
    user = await db.get(User, user_id)
    if not user or user.is_deleted or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Blacklist old refresh token
    exp = payload.get("exp")
    if exp:
        ttl = int(exp - datetime.now(timezone.utc).timestamp())
        if ttl > 0:
            await blacklist_token(old_jti, ttl, redis)

    # Generate new pair
    access_token = create_access_token(str(user.id), user.role)
    new_refresh_token, new_jti = create_refresh_token(str(user.id))

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "role": user.role,
        "full_name": user.full_name
    }

@router.post("/forgot-password", dependencies=[Depends(rate_limit_auth)])
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Generate and email a password reset OTP.
    """
    auth_service = AuthService(db, redis)
    user = await auth_service.repo.get_by_email(body.email)
    if not user:
        # Avoid user enumeration by returning a generic success message
        return {"message": "If the email is registered, a password reset code has been sent."}

    # Store reset OTP under a custom key
    otp = str(secrets.randbelow(900000) + 100000)
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()

    await redis.set(
        f"password_reset_otp:{user.id}",
        otp_hash,
        ex=settings.OTP_EXPIRE_SECONDS
    )

    try:
        await send_email(
            to_email=user.email,
            subject="LifeDrop: Reset your password",
            template="otp_verification",
            context={
                "otp": otp,
                "expires_minutes": settings.OTP_EXPIRE_SECONDS // 60
            }
        )
    except Exception as e:
        logger.error("forgot_password_email_failed", user_id=str(user.id), error=str(e))

    return {"message": "If the email is registered, a password reset code has been sent."}

@router.post("/reset-password", dependencies=[Depends(rate_limit_auth)])
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Verify password reset OTP and update password.
    """
    auth_service = AuthService(db, redis)
    user = await auth_service.repo.get_by_email(body.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check reset OTP
    otp_key = f"password_reset_otp:{user.id}"
    stored_hash = await redis.get(otp_key)
    if not stored_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code"
        )

    submitted_hash = hashlib.sha256(body.otp.encode()).hexdigest()
    stored_str = stored_hash.decode() if isinstance(stored_hash, bytes) else stored_hash

    if submitted_hash != stored_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code"
        )

    # Single-use: delete immediately
    await redis.delete(otp_key)

    # Update password
    user.password_hash = hash_password(body.new_password)
    await db.commit()

    return {"message": "Password reset successfully. You can now login with your new password."}
