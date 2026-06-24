import pytest
from decimal import Decimal
from datetime import date, datetime
from app.services.matching_service import MatchingService
from app.models.donor import Donor
from app.models.blood_request import BloodRequest

def test_donor_scoring_formula():
    # Instantiate matching service with dummy manager and notif service
    # since we are only testing the CPU-bound _score_donors method
    service = MatchingService(db=None, ws_manager=None, notification_service=None)

    # 1. Create a mock blood request
    request = BloodRequest(
        blood_type_needed="O+",
        urgency_level="urgent"
    )

    # 2. Setup mock donors
    # Donor A: Exact blood type match (O+), distance 10km, emergency available, availability 'always', 3 donations
    donor_a = Donor(
        blood_type="O+",
        is_available_emergency=True,
        availability="always",
        total_donations=3
    )
    donor_a.distance_km = 10.0

    # Donor B: Compatible blood type match (O-), distance 5km, emergency available, availability 'on_request', 1 donation
    donor_b = Donor(
        blood_type="O-",
        is_available_emergency=True,
        availability="on_request",
        total_donations=1
    )
    donor_b.distance_km = 5.0

    # Donor C: Exact blood type match (O+), distance 40km, not emergency available, availability 'unavailable', 10 donations (cap at 5)
    donor_c = Donor(
        blood_type="O+",
        is_available_emergency=False,
        availability="unavailable",
        total_donations=10
    )
    donor_c.distance_km = 40.0

    donors = [donor_a, donor_b, donor_c]

    # Calculate scores manually:
    # Formula:
    # Exact type match: +40 pts
    # Proximity: 30 - (distance_km * 0.3)
    # Emergency: +15 pts
    # Always: +10 pts
    # Donation count: min(total_donations, 5)

    # Donor A Score:
    # 40 (exact) + (30 - 10*0.3=27) + 15 (emergency) + 10 (always) + 3 (donations) = 40 + 27 + 15 + 10 + 3 = 95
    # Donor B Score:
    # 0 (compatible, not exact) + (30 - 5*0.3=28.5) + 15 (emergency) + 0 (on_request) + 1 (donation) = 28.5 + 15 + 1 = 44.5
    # Donor C Score:
    # 40 (exact) + (30 - 40*0.3=18) + 0 (not emergency) + 0 (unavailable) + 5 (cap 5) = 40 + 18 + 5 = 63

    scored = service._score_donors(donors, request)
    
    assert len(scored) == 3
    
    # Assert correct ordering (descending by score: A (95.0) -> C (63.0) -> B (44.5))
    assert scored[0][0] == donor_a
    assert scored[0][1] == 95.0
    
    assert scored[1][0] == donor_c
    assert scored[1][1] == 63.0
    
    assert scored[2][0] == donor_b
    assert scored[2][1] == 44.5
