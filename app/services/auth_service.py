from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from fastapi import HTTPException, status
from app.repositories.user_repo import UserRepository
from app.models.user import User
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    validate_password_strength, record_failed_login,
    is_login_locked, clear_failed_logins
)

class AuthService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.repo = UserRepository(db)

    async def register_user(self, email: str, phone: str, password: str, full_name: str, role: str = "donor") -> User:
        """Registers a new user after checking email/phone uniqueness and password strength."""
        if not validate_password_strength(password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters, include an uppercase, a lowercase, a number, and a special character."
            )

        existing_email = await self.repo.get_by_email(email)
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        existing_phone = await self.repo.get_by_phone(phone)
        if existing_phone:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number already registered")

        hashed = hash_password(password)
        new_user = User(
            email=email,
            phone=phone,
            password_hash=hashed,
            full_name=full_name,
            role=role,
            email_verified=False,
            is_active=True
        )
        user = await self.repo.create(new_user)
        return user

    async def authenticate_user(self, email: str, password: str, ip_address: str) -> dict:
        """Authenticates a user, enforcing brute-force lock protection."""
        if await is_login_locked(ip_address, self.redis):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. IP locked for 15 minutes."
            )

        user = await self.repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            await record_failed_login(ip_address, self.redis)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

        # Clear login failures on successful login
        await clear_failed_logins(ip_address, self.redis)

        # Update last login time
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.flush()

        access_token = create_access_token(str(user.id), user.role)
        refresh_token, jti = create_refresh_token(str(user.id))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "role": user.role,
            "full_name": user.full_name
        }
