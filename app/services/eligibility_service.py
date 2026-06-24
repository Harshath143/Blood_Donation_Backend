from datetime import date, timedelta
from app.models.donor import Donor

class EligibilityService:
    def check_eligibility(self, donor: Donor) -> tuple[bool, str | None]:
        """
        Verify donor's medical, age, weight, and timing eligibility.
        Returns (is_eligible, reason).
        """
        # 1. Weight criteria: Minimum 50kg
        if donor.weight_kg < 50:
            return False, "Weight must be at least 50 kg"

        # 2. Age criteria: Between 18 and 65 years
        today = date.today()
        age = today.year - donor.date_of_birth.year - (
            (today.month, today.day) < (donor.date_of_birth.month, donor.date_of_birth.day)
        )
        if age < 18:
            return False, "Donor must be at least 18 years old"
        if age > 65:
            return False, "Donor must be under 65 years old"

        # 3. Donation interval: 56 days since last donation
        if donor.last_donation_date:
            days_since_last = (today - donor.last_donation_date).days
            if days_since_last < 56:
                next_eligible_date = donor.last_donation_date + timedelta(days=56)
                return False, f"Must wait 56 days between donations. Next eligible date: {next_eligible_date.strftime('%Y-%m-%d')}"

        # 4. Medical conditions flag
        if donor.has_medical_conditions:
            return False, "Medical conditions flagged for review"

        return True, None

    def days_until_eligible(self, donor: Donor) -> int:
        if not donor.last_donation_date:
            return 0
        days_since_last = (date.today() - donor.last_donation_date).days
        remaining = 56 - days_since_last
        return max(0, remaining)
