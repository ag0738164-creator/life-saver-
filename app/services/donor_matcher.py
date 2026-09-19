from datetime import datetime, timezone
from app import db
from app.models import User, DonorProfile, EmergencyAlert

class EmergencyDonorMatcher:
    """
    Location-based emergency donor matching and compatibility resolver.
    When a hospital raises an urgent or critical request, this engine identifies
    all medically eligible compatible donors within geographic proximity.
    """

    # Transfusion Red Cell Compatibility Map
    # Key: Recipient Blood Group -> Value: List of Compatible Donor Blood Groups
    COMPATIBLE_DONORS_MAP = {
        'A+': ['A+', 'A-', 'O+', 'O-'],
        'A-': ['A-', 'O-'],
        'B+': ['B+', 'B-', 'O+', 'O-'],
        'B-': ['B-', 'O-'],
        'AB+': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
        'AB-': ['AB-', 'A-', 'B-', 'O-'],
        'O+': ['O+', 'O-'],
        'O-': ['O-']
    }

    @classmethod
    def get_compatible_donor_groups(cls, recipient_group):
        """Returns list of all compatible blood groups for a recipient."""
        return cls.COMPATIBLE_DONORS_MAP.get(recipient_group.upper(), [recipient_group.upper()])

    @classmethod
    def find_matching_donors(cls, recipient_group, target_city=None, max_results=15):
        """
        Queries all registered donors, filters for:
        1. Red cell compatibility
        2. 90-day medical cooldown eligibility
        3. Standard age and weight thresholds
        4. Geographic proximity (target city matches scored highest)
        """
        compatible_groups = cls.get_compatible_donor_groups(recipient_group)

        # Query all active donors with their profiles
        donors_query = User.query.filter_by(role='donor', is_active=True).all()

        matched_donors = []

        for donor in donors_query:
            prof = donor.donor_profile
            if not prof:
                continue

            # Check blood group compatibility
            if prof.blood_group not in compatible_groups:
                continue

            # Check medical eligibility (cooldown, age, weight)
            if not prof.is_eligible:
                continue

            # Score proximity
            is_local = False
            proximity_label = "Regional"
            proximity_badge = "bg-secondary"
            score = 10

            if target_city and donor.city:
                if target_city.strip().lower() == donor.city.strip().lower():
                    is_local = True
                    proximity_label = f"Local ({donor.city})"
                    proximity_badge = "bg-success"
                    score += 50
                elif target_city.strip().lower() in donor.city.strip().lower():
                    is_local = True
                    proximity_label = f"Nearby ({donor.city})"
                    proximity_badge = "bg-primary"
                    score += 30

            # Compatibility score: Exact match receives bonus over universal substitute
            is_exact = (prof.blood_group == recipient_group.upper())
            if is_exact:
                score += 30

            # Resting period score: More rested days = higher rank
            days_rest = prof.days_since_last_donation or 180
            score += min(20, days_rest // 10)

            # Reliability score: Lifetime donations count
            lifetime_count = donor.donations.count()
            score += min(15, lifetime_count * 3)

            matched_donors.append({
                'donor': donor,
                'profile': prof,
                'blood_group': prof.blood_group,
                'is_exact_match': is_exact,
                'is_local': is_local,
                'proximity_label': proximity_label,
                'proximity_badge': proximity_badge,
                'days_rested': days_rest,
                'lifetime_donations': lifetime_count,
                'score': score
            })

        # Sort by match score descending
        matched_donors.sort(key=lambda x: x['score'], reverse=True)

        return matched_donors[:max_results]

    @classmethod
    def dispatch_emergency_alerts(cls, request_id, donor_ids, hospital_name, blood_group, units_needed, urgency="Emergency"):
        """
        Dispatches simulated emergency SMS and Email alerts to selected matched donors
        and records EmergencyAlert audit entries.
        """
        dispatched_count = 0
        message_content = (
            f"URGENT LIFE SAVER ALERT: {hospital_name} has raised an {urgency.upper()} requisition "
            f"for {units_needed} unit(s) of {blood_group} blood. You are a compatible eligible donor nearby. "
            f"Please respond via your Life Saver Donor Portal or call 1800-BLOOD-LIFE."
        )

        for d_id in donor_ids:
            donor = db.session.get(User, d_id)
            if not donor or donor.role != 'donor':
                continue

            # Record SMS Alert
            sms_alert = EmergencyAlert(
                request_id=request_id,
                donor_id=donor.id,
                channel='SMS',
                recipient_contact=donor.phone or 'N/A',
                status='Delivered',
                message_content=message_content,
                sent_at=datetime.now(timezone.utc)
            )
            db.session.add(sms_alert)

            # Record Email Alert
            email_alert = EmergencyAlert(
                request_id=request_id,
                donor_id=donor.id,
                channel='Email',
                recipient_contact=donor.email,
                status='Delivered',
                message_content=message_content,
                sent_at=datetime.now(timezone.utc)
            )
            db.session.add(email_alert)

            dispatched_count += 1

        db.session.commit()
        return dispatched_count
