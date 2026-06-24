import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import UUID

from app.models.user import User
from app.models.blood_request import BloodRequest
from app.models.match import Match
from app.models.donor import Donor
from app.core.security import hash_password, create_access_token

@pytest_asyncio.fixture
async def request_user_headers(db_session: AsyncSession):
    user = User(
        email="requester@example.com",
        phone="+919876543215",
        password_hash=hash_password("Password123!"),
        full_name="Jane Requester",
        role="recipient",
        email_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    token = create_access_token(str(user.id), user.role)
    return {"Authorization": f"Bearer {token}"}, user

@pytest_asyncio.fixture
async def matched_donor(db_session: AsyncSession):
    user = User(
        email="donor_matched@example.com",
        phone="+919876543216",
        password_hash=hash_password("Password123!"),
        full_name="Matching Donor",
        role="donor",
        email_verified=True
    )
    db_session.add(user)
    await db_session.flush()

    # Create donor profile in Bangalore (same coordinates as our mock)
    from geoalchemy2.elements import WKTElement
    from decimal import Decimal
    donor = Donor(
        user_id=user.id,
        blood_type="O+",
        date_of_birth=date(1990, 1, 1),
        gender="female",
        weight_kg=Decimal("60.0"),
        city="Bengaluru",
        state="Karnataka",
        pincode="560001",
        latitude=Decimal("12.9716"),
        longitude=Decimal("77.5946"),
        location=WKTElement("POINT(77.5946 12.9716)", srid=4326),
        availability="on_request",
        is_available_emergency=True,
        is_verified=True,
        is_active=True
    )
    db_session.add(donor)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(donor)
    token = create_access_token(str(user.id), user.role)
    return {"Authorization": f"Bearer {token}"}, user, donor

from datetime import date

@pytest.mark.asyncio
async def test_create_blood_request_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
    request_user_headers,
    matched_donor
):
    headers, user = request_user_headers
    donor_headers, donor_user, donor = matched_donor

    # 1. Create a Request (with simulated PDF file upload)
    files = {
        "prescription": ("prescription.pdf", b"%PDF-1.4 mock pdf contents", "application/pdf")
    }
    form_data = {
        "patient_name": "Jane Patient",
        "patient_age": "30",
        "blood_type_needed": "O+",
        "units_needed": "2",
        "hospital_name": "Bangalore Hospital",
        "hospital_address": "456 Hospital Road",
        "city": "Bengaluru",
        "state": "Karnataka",
        "required_by": "2026-07-24T18:00:00",
        "urgency_level": "urgent",
        "contact_name": "Jane Requester",
        "contact_phone": "+919876543215",
        "case_description": "Accident emergency"
    }

    # Mock the Celery background trigger
    with patch("app.tasks.matching_tasks.trigger_matching_task.delay") as mock_delay:
        res = await client.post("/api/v1/requests", data=form_data, files=files, headers=headers)
        assert res.status_code == 200
        
        data = res.json()
        assert data["patient_name"] == "Jane Patient"
        assert data["blood_type_needed"] == "O+"
        assert data["status"] == "searching"
        assert data["prescription_name"] == "prescription.pdf"
        assert data["prescription_oid"] is not None
        
        req_id = data["id"]
        mock_delay.assert_called_once_with(req_id)

    # 2. Get Single Request Details
    get_res = await client.get(f"/api/v1/requests/{req_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["patient_name"] == "Jane Patient"

    # 3. Retrieve/Download prescription file
    download_res = await client.get(f"/api/v1/requests/{req_id}/prescription", headers=headers)
    assert download_res.status_code == 200
    assert download_res.content.startswith(b"%PDF")
    assert download_res.headers["content-type"] == "application/pdf"

    # 4. Mock the matching record and test donor responding
    # We manually create a Match in DB for the test
    match = Match(
        request_id=UUID(req_id),
        donor_id=donor.id,
        distance_km=0.0,
        compatibility="exact",
        status="notified"
    )
    db_session.add(match)
    await db_session.commit()

    # Donor responds: ACCEPT
    respond_payload = {
        "status": "accepted"
    }
    # Mock WebSocket manager to prevent sending errors during response dispatching
    with patch("app.websocket.manager.ws_manager.send_to_user", new_callable=AsyncMock) as mock_send:
        resp_res = await client.post(
            f"/api/v1/requests/{req_id}/matches/respond",
            json=respond_payload,
            headers=donor_headers
        )
        assert resp_res.status_code == 200
        assert resp_res.json()["status"] == "accepted"
        mock_send.assert_called_once()

    # 5. Fulfill the Request
    fulfill_res = await client.put(f"/api/v1/requests/{req_id}/fulfill", headers=headers)
    assert fulfill_res.status_code == 200
    assert fulfill_res.json()["status"] == "fulfilled"

    # Check match status updated to 'donated'
    await db_session.refresh(match)
    assert match.status == "donated"
