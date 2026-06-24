import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date

from app.models.user import User
from app.models.donor import Donor
from app.core.security import hash_password, create_access_token

@pytest_asyncio.fixture
async def donor_user_headers(db_session: AsyncSession):
    user = User(
        email="donor_test@example.com",
        phone="+919876543214",
        password_hash=hash_password("Password123!"),
        full_name="Donor Tester",
        role="donor",
        email_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    token = create_access_token(str(user.id), user.role)
    return {"Authorization": f"Bearer {token}"}, user

@pytest.mark.asyncio
async def test_create_and_update_profile(client: AsyncClient, db_session: AsyncSession, donor_user_headers):
    headers, user = donor_user_headers

    # 1. Create donor profile
    profile_payload = {
        "blood_type": "O+",
        "date_of_birth": "1995-05-15",
        "gender": "male",
        "weight_kg": 75.5,
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560001",
        "address": "123 Main St"
    }

    # Ensure geocoder is mocked (it's mocked in conftest.py to return Bangalore coordinates 12.9716, 77.5946)
    res = await client.post("/api/v1/donors/profile", json=profile_payload, headers=headers)
    assert res.status_code == 200
    
    data = res.json()
    assert data["blood_type"] == "O+"
    assert data["city"] == "Bengaluru"
    assert data["latitude"] == "12.971600"  # matches mock coordinates
    assert data["longitude"] == "77.594600"
    assert data["availability"] == "on_request"

    # 2. Check DB
    stmt = select(Donor).where(Donor.user_id == user.id)
    result = await db_session.execute(stmt)
    donor = result.scalar_one_or_none()
    assert donor is not None
    assert donor.blood_type == "O+"

    # 3. Retrieve profile
    get_res = await client.get("/api/v1/donors/me", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == str(donor.id)

    # 4. Update availability
    avail_payload = {
        "availability": "always",
        "is_available_emergency": True
    }
    avail_res = await client.put("/api/v1/donors/availability", json=avail_payload, headers=headers)
    assert avail_res.status_code == 200
    assert avail_res.json()["availability"] == "always"
    assert avail_res.json()["is_available_emergency"] is True

    # Check updated DB
    await db_session.refresh(donor)
    assert donor.availability == "always"
