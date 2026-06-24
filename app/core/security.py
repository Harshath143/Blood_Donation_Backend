import hashlib
import secrets
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from jose import jwt, JWTError
import bcrypt
from redis.asyncio import Redis
from fastapi import HTTPException
from app.config import get_settings

settings = get_settings()


# ── Password ──────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    pw_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    plain_bytes = plain.encode('utf-8')
    hashed_bytes = hashed.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


def validate_password_strength(password: str) -> bool:
    """
    Min 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special char.
    """
    pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#^])[A-Za-z\d@$!%*?&#^]{8,}$"
    return bool(re.match(pattern, password))


# ── JWT ───────────────────────────────────────────────────────────

def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {
            "sub": user_id,
            "role": role,
            "jti": str(uuid4()),
            "type": "access",
            "exp": expire,
            "iat": datetime.now(timezone.utc)
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

def create_refresh_token(user_id: str) -> tuple[str, str]:
    jti = str(uuid4())
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    token = jwt.encode(
        {
            "sub": user_id,
            "jti": jti,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.now(timezone.utc)
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return token, jti

async def verify_token(token: str, redis: Redis) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")

    jti = payload.get("jti")
    if jti and await redis.exists(f"blacklist:{jti}"):
        raise HTTPException(401, "Token has been revoked")

    return payload

async def blacklist_token(jti: str, ttl_seconds: int, redis: Redis):
    await redis.set(f"blacklist:{jti}", "1", ex=ttl_seconds)


# ── Email OTP ─────────────────────────────────────────────────────

async def send_email_otp(user_id: str, email: str, redis: Redis):
    from app.integrations.email import send_email

    otp = str(secrets.randbelow(900000) + 100000)  # 6-digit
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()

    await redis.set(
        f"otp:{user_id}",
        otp_hash,
        ex=settings.OTP_EXPIRE_SECONDS
    )

    await send_email(
        to_email=email,
        subject="Your LifeDrop verification code",
        template="otp_verification",
        context={
            "otp": otp,
            "expires_minutes": settings.OTP_EXPIRE_SECONDS // 60
        }
    )

async def verify_email_otp(user_id: str, otp: str, redis: Redis) -> bool:
    stored_hash = await redis.get(f"otp:{user_id}")
    if not stored_hash:
        return False

    submitted_hash = hashlib.sha256(otp.encode()).hexdigest()
    
    # decode if stored as bytes
    stored_str = stored_hash.decode() if isinstance(stored_hash, bytes) else stored_hash
    if submitted_hash != stored_str:
        return False

    await redis.delete(f"otp:{user_id}")  # single-use, always delete
    return True


# ── Login brute-force protection ─────────────────────────────────

async def record_failed_login(ip: str, redis: Redis):
    key = f"login_fail:{ip}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 900)   # 15-min window

async def is_login_locked(ip: str, redis: Redis) -> bool:
    count = await redis.get(f"login_fail:{ip}")
    return int(count or 0) >= 5

async def clear_failed_logins(ip: str, redis: Redis):
    await redis.delete(f"login_fail:{ip}")
