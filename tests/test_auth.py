import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.core.security import verify_password

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, db_session: AsyncSession, test_redis: Redis):
    # 1. Register a new donor
    payload = {
        "email": "donor@example.com",
        "phone": "+919876543210",
        "password": "Password123!",
        "full_name": "John Doe",
        "role": "donor"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["email"] == "donor@example.com"
    assert data["full_name"] == "John Doe"
    assert data["role"] == "donor"
    assert data["email_verified"] is False
    assert "password" not in data

    # 2. Check DB
    stmt = select(User).where(User.email == "donor@example.com")
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()
    assert user is not None
    assert verify_password("Password123!", user.password_hash)

    # 3. Check OTP was stored in Redis
    otp_hash = await test_redis.get(f"otp:{user.id}")
    assert otp_hash is not None

@pytest.mark.asyncio
async def test_login_and_throttling(client: AsyncClient, db_session: AsyncSession, test_redis: Redis):
    # Setup user
    from app.core.security import hash_password
    user = User(
        email="login@example.com",
        phone="+919876543211",
        password_hash=hash_password("Password123!"),
        full_name="Login Test",
        role="donor"
    )
    db_session.add(user)
    await db_session.commit()

    # 1. Failed Login Attempt
    fail_payload = {"email": "login@example.com", "password": "WrongPassword"}
    res = await client.post("/api/v1/auth/login", json=fail_payload)
    assert res.status_code == 401

    # 2. Lockout protection (5 fails)
    # We simulate 4 more failures to reach 5
    for _ in range(4):
        await client.post("/api/v1/auth/login", json=fail_payload)
    
    # 6th attempt should be locked out
    locked_res = await client.post("/api/v1/auth/login", json=fail_payload)
    assert locked_res.status_code == 429
    assert "locked" in locked_res.json()["detail"]

    # 3. Correct Login (with locked IP, should still fail because of lockout)
    success_payload = {"email": "login@example.com", "password": "Password123!"}
    res_correct_locked = await client.post("/api/v1/auth/login", json=success_payload)
    assert res_correct_locked.status_code == 429

@pytest.mark.asyncio
async def test_otp_verification_workflow(client: AsyncClient, db_session: AsyncSession, test_redis: Redis):
    # Register user
    payload = {
        "email": "verify@example.com",
        "phone": "+919876543212",
        "password": "Password123!",
        "full_name": "Verify User",
        "role": "donor"
    }
    await client.post("/api/v1/auth/register", json=payload)
    
    stmt = select(User).where(User.email == "verify@example.com")
    res = await db_session.execute(stmt)
    user = res.scalar_one()

    # Get OTP from Redis
    import hashlib
    otp_hash_bytes = await test_redis.get(f"otp:{user.id}")
    assert otp_hash_bytes is not None

    # Since OTP is randomly generated, we can override it in Redis to test verification
    # We set a known OTP code: "123456"
    test_otp = "123456"
    test_hash = hashlib.sha256(test_otp.encode()).hexdigest()
    await test_redis.set(f"otp:{user.id}", test_hash, ex=600)

    # 1. Invalid OTP
    verify_payload = {"email": "verify@example.com", "otp": "999999"}
    verify_res = await client.post("/api/v1/auth/verify-otp", json=verify_payload)
    assert verify_res.status_code == 400

    # 2. Valid OTP
    verify_payload["otp"] = test_otp
    verify_res = await client.post("/api/v1/auth/verify-otp", json=verify_payload)
    assert verify_res.status_code == 200
    assert verify_res.json()["message"] == "Email verified successfully"

    # 3. Check DB
    await db_session.refresh(user)
    assert user.email_verified is True

@pytest.mark.asyncio
async def test_token_refresh_and_revocation(client: AsyncClient, db_session: AsyncSession, test_redis: Redis):
    # Setup user
    from app.core.security import hash_password
    user = User(
        email="refresh@example.com",
        phone="+919876543213",
        password_hash=hash_password("Password123!"),
        full_name="Refresh Test",
        role="donor"
    )
    db_session.add(user)
    await db_session.commit()

    # Login to get tokens
    login_res = await client.post("/api/v1/auth/login", json={"email": "refresh@example.com", "password": "Password123!"})
    tokens = login_res.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # 1. Refresh token
    refresh_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens

    # 2. Reusing old refresh token (should fail because it was blacklisted on refresh)
    reuse_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse_res.status_code == 401
