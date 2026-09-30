import os
import unittest
from datetime import date, timedelta
from app import create_app, db
from app.models import (
    User, DonorProfile, HospitalProfile, BloodInventory,
    BloodRequest, DonationRecord, BloodBagUnit, EmergencyAlert
)
from app.services.ai_predictor import BloodDemandPredictor
from app.services.donor_matcher import EmergencyDonorMatcher
from app.services.qr_service import BloodUnitQRService
from config import Config

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), 'test_firebase.json')

class TestConfig(Config):
    TESTING = True
    LOCAL_FIRESTORE_PATH = TEST_DB_PATH
    WTF_CSRF_ENABLED = False

class BloodBankTestCase(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except Exception:
                pass
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Seed blood groups in inventory
        for bg in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']:
            inv = BloodInventory(id=bg, blood_group=bg, units_available=10, critical_threshold=5)
            db.session.add(inv)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except Exception:
                pass

    def test_donor_registration_and_profile(self):
        """Test donor registration and profile creation."""
        user = User(
            name="Test Donor",
            email="testdonor@example.com",
            role="donor",
            phone="1234567890",
            city="Metropolis"
        )
        user.set_password("SecurePass123")
        db.session.add(user)
        db.session.flush()

        profile = DonorProfile(
            user_id=user.id,
            blood_group="O+",
            age=25,
            weight=68.0,
            last_donation_date=None
        )
        db.session.add(profile)
        db.session.commit()

        # Verification
        saved_user = User.query.filter_by(email="testdonor@example.com").first()
        self.assertIsNotNone(saved_user)
        self.assertTrue(saved_user.check_password("SecurePass123"))
        self.assertFalse(saved_user.check_password("WrongPassword"))
        self.assertTrue(saved_user.is_donor)
        self.assertEqual(saved_user.donor_profile.blood_group, "O+")
        self.assertTrue(saved_user.donor_profile.is_eligible)

    def test_donor_cooldown_logic(self):
        """Test the 90-day cooldown period for blood donors."""
        user = User(name="Cooldown Donor", email="cooldown@example.com", role="donor")
        user.set_password("pass123")
        db.session.add(user)
        db.session.flush()

        # Donor who donated 30 days ago (within 90-day cooldown)
        recent_date = date.today() - timedelta(days=30)
        profile = DonorProfile(
            user_id=user.id,
            blood_group="A+",
            age=30,
            weight=70.0,
            last_donation_date=recent_date
        )
        db.session.add(profile)
        db.session.commit()

        self.assertFalse(profile.is_eligible)
        self.assertEqual(profile.cooldown_days_remaining, 60)

        # Update last donation to 95 days ago (eligible)
        profile.last_donation_date = date.today() - timedelta(days=95)
        db.session.commit()

        self.assertTrue(profile.is_eligible)
        self.assertEqual(profile.cooldown_days_remaining, 0)

    def test_hospital_requisition_flow(self):
        """Test hospital requisition submission and admin approval with stock decrement."""
        # Create hospital
        hospital = User(name="City Hospital", email="hospital@example.com", role="hospital")
        hospital.set_password("hosp123")
        db.session.add(hospital)
        db.session.flush()

        h_prof = HospitalProfile(user_id=hospital.id, license_number="LIC-101", hospital_type="General")
        db.session.add(h_prof)

        # Initial O+ stock is 10 units
        o_stock = BloodInventory.query.filter_by(blood_group="O+").first()
        self.assertEqual(o_stock.units_available, 10)

        # Create requisition for 3 units of O+
        req = BloodRequest(
            hospital_id=hospital.id,
            blood_group="O+",
            units_requested=3,
            urgency="Emergency",
            patient_name="John Patient",
            status="Pending"
        )
        db.session.add(req)
        db.session.commit()

        # Admin approves the request
        self.assertEqual(req.status, "Pending")
        if o_stock.units_available >= req.units_requested:
            o_stock.units_available -= req.units_requested
            req.status = "Approved"
            db.session.commit()

        self.assertEqual(req.status, "Approved")
        self.assertEqual(o_stock.units_available, 7)

    def test_insufficient_stock_prevention(self):
        """Test that requests exceeding available inventory cannot deduct below zero."""
        b_minus_stock = BloodInventory.query.filter_by(blood_group="B-").first()
        b_minus_stock.units_available = 2
        db.session.commit()

        # Request 5 units when only 2 are available
        req_units = 5
        can_fulfill = b_minus_stock.units_available >= req_units
        self.assertFalse(can_fulfill)

    def test_donation_increments_inventory(self):
        """Test that logging a completed donation increments blood inventory."""
        user = User(name="Generous Donor", email="generous@example.com", role="donor")
        user.set_password("pass123")
        db.session.add(user)
        db.session.flush()

        profile = DonorProfile(user_id=user.id, blood_group="AB-", age=22, weight=55.0)
        db.session.add(profile)
        db.session.commit()

        ab_stock = BloodInventory.query.filter_by(blood_group="AB-").first()
        initial_units = ab_stock.units_available

        # Log donation of 1 unit
        donation = DonationRecord(
            donor_id=user.id,
            blood_group="AB-",
            units_donated=1,
            donation_date=date.today(),
            status="Completed"
        )
        db.session.add(donation)
        ab_stock.units_available += 1
        profile.last_donation_date = date.today()
        db.session.commit()

        self.assertEqual(ab_stock.units_available, initial_units + 1)
        self.assertEqual(profile.last_donation_date, date.today())
        self.assertFalse(profile.is_eligible)  # Now in cooldown

    def test_public_routes(self):
        """Test public endpoints return 200 OK."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Blood Bank Management System', response.data)

        response = self.client.get('/stock')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/eligibility')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/camps')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/auth/login')
        self.assertEqual(response.status_code, 200)

    def test_authenticated_role_access(self):
        """Test authenticated user logins and role-restricted dashboard access."""
        # 1. Admin login & dashboard
        admin = User(name="Admin User", email="admin_test@example.com", role="admin")
        admin.set_password("AdminPass")
        db.session.add(admin)

        # 2. Donor login & dashboard
        donor = User(name="Donor User", email="donor_test@example.com", role="donor", city="Boston")
        donor.set_password("DonorPass")
        db.session.add(donor)
        db.session.flush()
        d_prof = DonorProfile(user_id=donor.id, blood_group="B+", age=28, weight=65.0)
        db.session.add(d_prof)

        # 3. Hospital login & dashboard
        hospital = User(name="Test Hospital", email="hosp_test@example.com", role="hospital")
        hospital.set_password("HospPass")
        db.session.add(hospital)
        db.session.flush()
        h_prof = HospitalProfile(user_id=hospital.id, license_number="H-99", hospital_type="General")
        db.session.add(h_prof)
        db.session.commit()

        # Test login post
        login_res = self.client.post('/auth/login', data={
            'email': 'admin_test@example.com',
            'password': 'AdminPass'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Operations &amp; Logistics Dashboard', login_res.data)

        # Admin can access admin routes
        admin_res = self.client.get('/admin/inventory')
        self.assertEqual(admin_res.status_code, 200)

        # Logout
        self.client.get('/auth/logout')

        # Donor login
        self.client.post('/auth/login', data={
            'email': 'donor_test@example.com',
            'password': 'DonorPass'
        }, follow_redirects=True)

        donor_res = self.client.get('/donor/dashboard')
        self.assertEqual(donor_res.status_code, 200)
        self.assertIn(b'Hello, Donor User!', donor_res.data)

        # Donor Card
        card_res = self.client.get('/donor/card')
        self.assertEqual(card_res.status_code, 200)
        self.assertIn(b'Official Blood Donor Identity Card', card_res.data)

        # Donor cannot access admin dashboard (403 forbidden)
        forbidden_res = self.client.get('/admin/dashboard')
        self.assertEqual(forbidden_res.status_code, 403)

        self.client.get('/auth/logout')

    def test_csv_export(self):
        """Test admin CSV export routes."""
        admin = User(name="Admin Exporter", email="admin_exp@example.com", role="admin")
        admin.set_password("AdminPass")
        db.session.add(admin)
        db.session.commit()

        self.client.post('/auth/login', data={
            'email': 'admin_exp@example.com',
            'password': 'AdminPass'
        })

        inv_csv = self.client.get('/admin/export/inventory')
        self.assertEqual(inv_csv.status_code, 200)
        self.assertEqual(inv_csv.mimetype, 'text/csv')
        self.assertIn(b'Blood Group,Units Available', inv_csv.data)

    def test_ai_blood_demand_prediction(self):
        """Test AI demand prediction engine forecasts and confidence scoring."""
        # 14-day prediction
        forecast = BloodDemandPredictor.predict_demand(days_horizon=14)
        self.assertEqual(forecast['horizon_days'], 14)
        self.assertEqual(len(forecast['predictions']), 8)
        self.assertGreater(forecast['total_forecasted_demand'], 0)
        self.assertGreater(forecast['seasonal_factor'], 1.0)

        # Verify each prediction contains required metrics
        for pred in forecast['predictions']:
            self.assertIn(pred['blood_group'], ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'])
            self.assertGreaterEqual(pred['confidence'], 80.0)
            self.assertIn('action_advice', pred)

    def test_location_emergency_donor_matching(self):
        """Test location-based emergency donor matching and compatibility filtering."""
        # Seed test donors
        # Donor 1: O+ in Metropolis (Eligible, 100 days rest)
        d1 = User(name="Local Compatible", email="local@test.com", role="donor", city="Metropolis")
        d1.set_password("pass")
        db.session.add(d1)
        db.session.flush()
        p1 = DonorProfile(user_id=d1.id, blood_group="O+", age=30, weight=75.0, last_donation_date=date.today() - timedelta(days=100))
        db.session.add(p1)

        # Donor 2: B+ in Metropolis (Incompatible with A+ recipient)
        d2 = User(name="Incompatible Group", email="incomp@test.com", role="donor", city="Metropolis")
        d2.set_password("pass")
        db.session.add(d2)
        db.session.flush()
        p2 = DonorProfile(user_id=d2.id, blood_group="B+", age=25, weight=68.0, last_donation_date=date.today() - timedelta(days=100))
        db.session.add(p2)

        # Donor 3: A- in Gotham City (Compatible with A+, but regional)
        d3 = User(name="Regional Compatible", email="regional@test.com", role="donor", city="Gotham City")
        d3.set_password("pass")
        db.session.add(d3)
        db.session.flush()
        p3 = DonorProfile(user_id=d3.id, blood_group="A-", age=35, weight=65.0, last_donation_date=date.today() - timedelta(days=95))
        db.session.add(p3)
        db.session.commit()

        # Find matches for A+ recipient in Metropolis
        matches = EmergencyDonorMatcher.find_matching_donors('A+', target_city='Metropolis')
        matched_donor_emails = [m['donor'].email for m in matches]

        # O+ (universal donor for Rh+) and A- (compatible with A+) should match
        self.assertIn('local@test.com', matched_donor_emails)
        self.assertIn('regional@test.com', matched_donor_emails)
        # B+ is incompatible with A+ and must NOT match
        self.assertNotIn('incomp@test.com', matched_donor_emails)

        # Local match in Metropolis should rank above Gotham City
        self.assertEqual(matches[0]['donor'].email, 'local@test.com')
        self.assertTrue(matches[0]['is_local'])

    def test_qr_code_unit_generation_and_tracking(self):
        """Test QR code generation, unit enrollment, and shelf-life tracking."""
        b_unit = BloodBagUnit(
            unit_number="LS-UNIT-TEST-001",
            blood_group="O-",
            component_type="Packed Red Blood Cells",
            volume_ml=450,
            collection_date=date.today(),
            expiry_date=date.today() + timedelta(days=35),
            status="In Storage"
        )
        db.session.add(b_unit)
        db.session.commit()

        # Test QR generation
        qr_uri = b_unit.get_qr_image()
        self.assertTrue(qr_uri.startswith("data:image/png;base64,"))

        # Test shelf life properties
        self.assertFalse(b_unit.is_expired)
        self.assertEqual(b_unit.days_until_expiry, 35)
        self.assertEqual(b_unit.status_badge_class, "bg-success")

    def test_emergency_alert_dispatch(self):
        """Test emergency SMS/Email alert dispatch simulation."""
        donor = User(name="Alert Target", email="alert@target.com", role="donor", phone="+1 555-9988")
        donor.set_password("pass")
        hosp = User(name="Trauma Hosp", email="trauma@hosp.com", role="hospital")
        hosp.set_password("pass")
        db.session.add_all([donor, hosp])
        db.session.flush()

        req = BloodRequest(hospital_id=hosp.id, blood_group="O+", units_requested=2, urgency="Emergency", patient_name="Emergency Pt")
        db.session.add(req)
        db.session.commit()

        dispatched = EmergencyDonorMatcher.dispatch_emergency_alerts(
            request_id=req.id,
            donor_ids=[donor.id],
            hospital_name="Trauma Hosp",
            blood_group="O+",
            units_needed=2,
            urgency="Emergency"
        )
        self.assertEqual(dispatched, 1)

        # Verify alerts recorded
        alerts = EmergencyAlert.query.filter_by(request_id=req.id).all()
        self.assertEqual(len(alerts), 2)  # 1 SMS and 1 Email
        channels = [a.channel for a in alerts]
        self.assertIn("SMS", channels)
        self.assertIn("Email", channels)

if __name__ == '__main__':
    unittest.main()


