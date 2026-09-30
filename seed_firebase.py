import os
from datetime import date, datetime, timedelta, timezone
from app import create_app
from app.firebase_db import get_firebase_db, get_db_mode
from app.models import (
    User, DonorProfile, HospitalProfile, BloodInventory,
    BloodRequest, DonationRecord, DonationCamp,
    BloodBagUnit, EmergencyAlert, db
)

def seed_firebase():
    """Populates Firebase Firestore with complete demo dataset."""
    app = create_app()
    with app.app_context():
        firestore_db = get_firebase_db()
        mode = get_db_mode()
        print(f"[Firebase] Initializing Firebase Seeding in mode: [{mode}]")

        # Check if already seeded
        existing_admin = User.query.filter_by(role='admin').first()
        if existing_admin:
            print("Notice: Firebase already contains records. Clearing or updating data...")

        # -------------------------------------------------------------
        # 1. Blood Inventory (All 8 Groups)
        # -------------------------------------------------------------
        inventory_data = [
            ('A+', 18, 5),
            ('A-', 6, 5),
            ('B+', 15, 5),
            ('B-', 4, 5),   # Critical
            ('AB+', 10, 4),
            ('AB-', 3, 4),  # Critical
            ('O+', 24, 6),
            ('O-', 5, 5),   # Critical universal donor
        ]
        for bg, units, thresh in inventory_data:
            inv = BloodInventory.query.filter_by(blood_group=bg).first()
            if not inv:
                inv = BloodInventory(
                    id=bg,
                    blood_group=bg,
                    units_available=units,
                    critical_threshold=thresh,
                    last_updated=datetime.now(timezone.utc)
                )
            else:
                inv.units_available = units
                inv.critical_threshold = thresh
                inv.last_updated = datetime.now(timezone.utc)
            inv.save()
        print("[OK] Blood Inventory initialized (8 blood groups).")

        # -------------------------------------------------------------
        # 2. Administrator Account
        # -------------------------------------------------------------
        admin = User.query.filter_by(email="admin@bloodbank.org").first()
        if not admin:
            admin = User(
                id="1",
                name="Chief Medical Administrator",
                email="admin@bloodbank.org",
                role="admin",
                phone="+1 (800) 555-0100",
                city="Metropolis",
                address="742 Central Blood Repository Blvd",
                created_at=datetime.now(timezone.utc)
            )
            admin.set_password("Admin@123")
            admin.save()
        print("[OK] Admin account initialized: admin@bloodbank.org / Admin@123")

        # -------------------------------------------------------------
        # 3. Hospitals & Profiles
        # -------------------------------------------------------------
        hospitals_data = [
            {
                "id": "2",
                "name": "City General Hospital",
                "email": "citygeneral@hospital.org",
                "phone": "+1 555-0111",
                "city": "Metropolis",
                "address": "100 Medical Center Way",
                "license": "HOSP-MED-2024-001",
                "type": "General Hospital",
                "emergency": "+1 555-9111"
            },
            {
                "id": "3",
                "name": "St. Jude Trauma & Emergency Center",
                "email": "stjude@hospital.org",
                "phone": "+1 555-0112",
                "city": "Gotham City",
                "address": "450 Rescue Ave",
                "license": "HOSP-TRAUMA-9821",
                "type": "Trauma / Emergency Center",
                "emergency": "+1 555-9112"
            },
            {
                "id": "4",
                "name": "Metro Children's Specialty Clinic",
                "email": "metro.children@hospital.org",
                "phone": "+1 555-0113",
                "city": "Star City",
                "address": "88 Hope Pediatric Plaza",
                "license": "HOSP-PED-3310",
                "type": "Specialty Clinic",
                "emergency": "+1 555-9113"
            },
            {
                "id": "5",
                "name": "Memorial Heart & Surgical Institute",
                "email": "memorial@hospital.org",
                "phone": "+1 555-0114",
                "city": "Central City",
                "address": "520 Cardiology Way",
                "license": "HOSP-SURG-7744",
                "type": "Surgical Institute",
                "emergency": "+1 555-9114"
            }
        ]

        for h in hospitals_data:
            user = User.query.filter_by(email=h["email"]).first()
            if not user:
                user = User(
                    id=h["id"],
                    name=h["name"],
                    email=h["email"],
                    role="hospital",
                    phone=h["phone"],
                    city=h["city"],
                    address=h["address"],
                    created_at=datetime.now(timezone.utc)
                )
                user.set_password("Hospital@123")
                user.save()

            prof = HospitalProfile.query.filter_by(user_id=user.id).first()
            if not prof:
                prof = HospitalProfile(
                    id=user.id,
                    user_id=user.id,
                    license_number=h["license"],
                    hospital_type=h["type"],
                    emergency_contact=h["emergency"],
                    is_verified=True
                )
                prof.save()
        print(f"[OK] {len(hospitals_data)} Hospitals registered & verified.")

        # -------------------------------------------------------------
        # 4. Donors & Profiles (All 8 Blood Groups)
        # -------------------------------------------------------------
        donors_data = [
            {
                "id": "6",
                "name": "John Doe",
                "email": "john.doe@email.com",
                "phone": "+1 555-0201",
                "city": "Metropolis",
                "address": "12 Oak Street, Apt 4B",
                "blood_group": "O+",
                "gender": "Male",
                "age": 32,
                "weight": 75.0,
                "last_donation": date.today() - timedelta(days=120),  # Eligible
                "notes": "Regular volunteer donor, universal recipient preferred."
            },
            {
                "id": "7",
                "name": "Sarah Miller",
                "email": "sarah.m@email.com",
                "phone": "+1 555-0202",
                "city": "Metropolis",
                "address": "34 Maple Ave",
                "blood_group": "A+",
                "gender": "Female",
                "age": 28,
                "weight": 58.0,
                "last_donation": date.today() - timedelta(days=95),   # Eligible
                "notes": "No allergies, excellent hemoglobin levels."
            },
            {
                "id": "8",
                "name": "Alex Wong",
                "email": "alex.w@email.com",
                "phone": "+1 555-0203",
                "city": "Gotham City",
                "address": "78 Pine Boulevard",
                "blood_group": "B+",
                "gender": "Male",
                "age": 35,
                "weight": 80.0,
                "last_donation": date.today() - timedelta(days=30),   # Under cooldown (60 days left)
                "notes": "Recent whole blood donation, in cooldown period."
            },
            {
                "id": "9",
                "name": "Elena Rostova",
                "email": "elena.r@email.com",
                "phone": "+1 555-0204",
                "city": "Star City",
                "address": "210 Cedar Street",
                "blood_group": "AB+",
                "gender": "Female",
                "age": 29,
                "weight": 62.0,
                "last_donation": None,                                 # First time donor
                "notes": "Universal plasma donor. First time registrant."
            },
            {
                "id": "10",
                "name": "Marcus Vance",
                "email": "marcus.v@email.com",
                "phone": "+1 555-0205",
                "city": "Metropolis",
                "address": "55 Birch Lane",
                "blood_group": "O-",
                "gender": "Male",
                "age": 41,
                "weight": 84.0,
                "last_donation": date.today() - timedelta(days=150),  # Eligible
                "notes": "Universal Red Cell Donor (O-Negative). Emergency on-call volunteer."
            },
            {
                "id": "11",
                "name": "Priya Sharma",
                "email": "priya.s@email.com",
                "phone": "+1 555-0206",
                "city": "Central City",
                "address": "90 Elm Court",
                "blood_group": "A-",
                "gender": "Female",
                "age": 26,
                "weight": 54.0,
                "last_donation": date.today() - timedelta(days=100),  # Eligible
                "notes": "Regular corporate camp participant."
            },
            {
                "id": "12",
                "name": "David Kim",
                "email": "david.k@email.com",
                "phone": "+1 555-0207",
                "city": "Gotham City",
                "address": "142 Walnut Way",
                "blood_group": "B-",
                "gender": "Male",
                "age": 33,
                "weight": 71.0,
                "last_donation": date.today() - timedelta(days=110),  # Eligible
                "notes": "Rare B- donor. Dedicated crisis donor."
            },
            {
                "id": "13",
                "name": "Chloe Taylor",
                "email": "chloe.t@email.com",
                "phone": "+1 555-0208",
                "city": "Star City",
                "address": "67 Willow Road",
                "blood_group": "AB-",
                "gender": "Female",
                "age": 30,
                "weight": 60.0,
                "last_donation": date.today() - timedelta(days=92),   # Eligible
                "notes": "Rare AB- donor. Excellent health."
            }
        ]

        for d in donors_data:
            user = User.query.filter_by(email=d["email"]).first()
            if not user:
                user = User(
                    id=d["id"],
                    name=d["name"],
                    email=d["email"],
                    role="donor",
                    phone=d["phone"],
                    city=d["city"],
                    address=d["address"],
                    created_at=datetime.now(timezone.utc) - timedelta(days=180)
                )
                user.set_password("Donor@123")
                user.save()

            prof = DonorProfile.query.filter_by(user_id=user.id).first()
            if not prof:
                prof = DonorProfile(
                    id=user.id,
                    user_id=user.id,
                    blood_group=d["blood_group"],
                    gender=d["gender"],
                    age=d["age"],
                    weight=d["weight"],
                    last_donation_date=d["last_donation"],
                    medical_notes=d["notes"]
                )
                prof.save()
        print(f"[OK] {len(donors_data)} Donors registered with medical eligibility profiles.")

        # -------------------------------------------------------------
        # 5. Donation Camps
        # -------------------------------------------------------------
        camps_data = [
            {
                "id": "1",
                "title": "Metropolis Annual Community Blood Drive",
                "organized_by": "Red Cross & Life Saver Central",
                "location": "Metropolis Convention Center, Hall A",
                "city": "Metropolis",
                "camp_date": date.today() + timedelta(days=7),
                "start_time": "09:00 AM",
                "end_time": "05:00 PM",
                "contact_person": "Dr. Angela Davies",
                "contact_phone": "+1 555-8801",
                "description": "Massive community donation campaign with mobile phlebotomy units and health checkups.",
                "status": "Upcoming"
            },
            {
                "id": "2",
                "title": "Gotham University Student Donor Camp",
                "organized_by": "Gotham University Medical Club",
                "location": "Student Activity Center, South Campus",
                "city": "Gotham City",
                "camp_date": date.today() + timedelta(days=14),
                "start_time": "10:00 AM",
                "end_time": "04:00 PM",
                "contact_person": "Prof. Bruce Thomas",
                "contact_phone": "+1 555-8802",
                "description": "Youth awareness drive focusing on first-time donors and rare group registration.",
                "status": "Upcoming"
            },
            {
                "id": "3",
                "title": "Corporate Wellness Blood Donation Day",
                "organized_by": "Apex Tech Group & Life Saver",
                "location": "Apex Tower, 12th Floor Atrium",
                "city": "Star City",
                "camp_date": date.today() + timedelta(days=21),
                "start_time": "09:30 AM",
                "end_time": "03:30 PM",
                "contact_person": "Rachel Scott",
                "contact_phone": "+1 555-8803",
                "description": "Annual corporate responsibility blood drive open to all tech park employees.",
                "status": "Upcoming"
            },
            {
                "id": "4",
                "title": "Memorial Day Emergency Surge Drive",
                "organized_by": "National Blood Reserve",
                "location": "Central City Civic Pavilion",
                "city": "Central City",
                "camp_date": date.today() - timedelta(days=25),
                "start_time": "08:00 AM",
                "end_time": "06:00 PM",
                "contact_person": "Capt. James Miller",
                "contact_phone": "+1 555-8804",
                "description": "Successfully concluded regional emergency surge donation event.",
                "status": "Completed"
            }
        ]
        for c in camps_data:
            camp = DonationCamp.get(c["id"])
            if not camp:
                camp = DonationCamp(**c)
                camp.save()
        print(f"[OK] {len(camps_data)} Donation Camps scheduled.")

        # -------------------------------------------------------------
        # 6. Donation History Records
        # -------------------------------------------------------------
        donations_data = [
            {"id": "1", "donor_id": "6", "camp_id": "4", "blood_group": "O+", "units_donated": 1, "donation_date": date.today() - timedelta(days=120), "status": "Completed", "verified_by": "Dr. A. Davies", "notes": "Standard donation, perfectly tolerated."},
            {"id": "2", "donor_id": "6", "camp_id": None, "blood_group": "O+", "units_donated": 1, "donation_date": date.today() - timedelta(days=220), "status": "Completed", "verified_by": "Nurse Kelly", "notes": "Blood bank walk-in donation."},
            {"id": "3", "donor_id": "7", "camp_id": "4", "blood_group": "A+", "units_donated": 1, "donation_date": date.today() - timedelta(days=95), "status": "Completed", "verified_by": "Dr. A. Davies", "notes": "Routine whole blood collection."},
            {"id": "4", "donor_id": "8", "camp_id": None, "blood_group": "B+", "units_donated": 1, "donation_date": date.today() - timedelta(days=30), "status": "Completed", "verified_by": "Dr. S. Thorne", "notes": "Urgent direct donor request."},
            {"id": "5", "donor_id": "10", "camp_id": "4", "blood_group": "O-", "units_donated": 1, "donation_date": date.today() - timedelta(days=150), "status": "Completed", "verified_by": "Dr. A. Davies", "notes": "Emergency universal reserve collection."},
            {"id": "6", "donor_id": "10", "camp_id": None, "blood_group": "O-", "units_donated": 1, "donation_date": date.today() - timedelta(days=260), "status": "Completed", "verified_by": "Dr. Evans", "notes": "Walk-in donation."},
            {"id": "7", "donor_id": "11", "camp_id": "4", "blood_group": "A-", "units_donated": 1, "donation_date": date.today() - timedelta(days=100), "status": "Completed", "verified_by": "Dr. Thorne", "notes": "Packed RBC processing."},
            {"id": "8", "donor_id": "12", "camp_id": None, "blood_group": "B-", "units_donated": 1, "donation_date": date.today() - timedelta(days=110), "status": "Completed", "verified_by": "Nurse Kelly", "notes": "Scheduled apheresis."},
            {"id": "9", "donor_id": "13", "camp_id": "4", "blood_group": "AB-", "units_donated": 1, "donation_date": date.today() - timedelta(days=92), "status": "Completed", "verified_by": "Dr. A. Davies", "notes": "Rare group stock replenishment."},
            {"id": "10", "donor_id": "6", "camp_id": "1", "blood_group": "O+", "units_donated": 1, "donation_date": date.today() + timedelta(days=7), "status": "Scheduled", "verified_by": None, "notes": "Upcoming camp slot booked by donor."}
        ]
        for d in donations_data:
            rec = DonationRecord.get(d["id"])
            if not rec:
                rec = DonationRecord(**d)
                rec.save()
        print(f"[OK] {len(donations_data)} Donation history records seeded.")

        # -------------------------------------------------------------
        # 7. Hospital Blood Requisitions
        # -------------------------------------------------------------
        requests_data = [
            {
                "id": "1",
                "hospital_id": "2",
                "blood_group": "O+",
                "units_requested": 4,
                "urgency": "Emergency",
                "patient_name": "Alexander Stone",
                "patient_case_no": "TRAUMA-2026-904",
                "reason": "Massive hemorrhage following multi-vehicle traffic accident on Highway 9.",
                "status": "Pending",
                "admin_notes": None,
                "created_at": datetime.now(timezone.utc) - timedelta(hours=2)
            },
            {
                "id": "2",
                "hospital_id": "3",
                "blood_group": "A-",
                "units_requested": 2,
                "urgency": "Critical",
                "patient_name": "Maria Gonzalez",
                "patient_case_no": "OBS-55421",
                "reason": "Severe postpartum hemorrhage with rare antibody profile.",
                "status": "Pending",
                "admin_notes": None,
                "created_at": datetime.now(timezone.utc) - timedelta(hours=5)
            },
            {
                "id": "3",
                "hospital_id": "4",
                "blood_group": "B+",
                "units_requested": 3,
                "urgency": "Normal",
                "patient_name": "Leo Patel (Age 8)",
                "patient_case_no": "PED-ONC-112",
                "reason": "Thalassemia major transfusion support - weekly protocol.",
                "status": "Approved",
                "admin_notes": "Approved by Chief Administrator. Ready for cold transit dispatch.",
                "created_at": datetime.now(timezone.utc) - timedelta(days=1),
                "processed_at": datetime.now(timezone.utc) - timedelta(hours=18)
            },
            {
                "id": "4",
                "hospital_id": "5",
                "blood_group": "O-",
                "units_requested": 2,
                "urgency": "Emergency",
                "patient_name": "David Reynolds",
                "patient_case_no": "CARD-OR-882",
                "reason": "Emergency aortic aneurysm dissection repair in OR 4.",
                "status": "Dispensed",
                "admin_notes": "Dispensed via rapid medical courier. Cold chain box #7.",
                "created_at": datetime.now(timezone.utc) - timedelta(days=2),
                "processed_at": datetime.now(timezone.utc) - timedelta(days=2, hours=-1)
            },
            {
                "id": "5",
                "hospital_id": "2",
                "blood_group": "AB+",
                "units_requested": 1,
                "urgency": "Normal",
                "patient_name": "Arthur Pendelton",
                "patient_case_no": "SURG-4401",
                "reason": "Scheduled total hip arthroplasty pre-op crossmatch.",
                "status": "Dispensed",
                "admin_notes": "Delivered to City General pathology cold storage.",
                "created_at": datetime.now(timezone.utc) - timedelta(days=4),
                "processed_at": datetime.now(timezone.utc) - timedelta(days=3)
            },
            {
                "id": "6",
                "hospital_id": "3",
                "blood_group": "B-",
                "units_requested": 5,
                "urgency": "Critical",
                "patient_name": "James Henderson",
                "patient_case_no": "ICU-9921",
                "reason": "Severe septic shock with secondary DIC coagulopathy.",
                "status": "Approved",
                "admin_notes": "Approved 5 units from cold vault compartment B.",
                "created_at": datetime.now(timezone.utc) - timedelta(hours=14),
                "processed_at": datetime.now(timezone.utc) - timedelta(hours=10)
            },
            {
                "id": "7",
                "hospital_id": "4",
                "blood_group": "AB-",
                "units_requested": 4,
                "urgency": "Critical",
                "patient_name": "Samantha Lee",
                "patient_case_no": "PED-SURG-77",
                "reason": "Complex congenital heart defect repair with cardiopulmonary bypass.",
                "status": "Pending",
                "admin_notes": None,
                "created_at": datetime.now(timezone.utc) - timedelta(minutes=45)
            }
        ]
        for r in requests_data:
            req = BloodRequest.get(r["id"])
            if not req:
                req = BloodRequest(**r)
                req.save()
        print(f"[OK] {len(requests_data)} Hospital blood requisitions initialized.")

        # -------------------------------------------------------------
        # 8. Blood Bag Units with QR Code Tracking
        # -------------------------------------------------------------
        today = date.today()
        units_data = [
            {"id": "1", "unit_number": "LS-UNIT-2026-0001", "blood_group": "O+", "donor_id": "6", "donation_id": "1", "component_type": "Packed Red Blood Cells", "volume_ml": 450, "collection_date": today - timedelta(days=10), "expiry_date": today + timedelta(days=25), "storage_location": "Vault A, Shelf 1", "status": "In Storage"},
            {"id": "2", "unit_number": "LS-UNIT-2026-0002", "blood_group": "O+", "donor_id": "6", "donation_id": "2", "component_type": "Fresh Frozen Plasma", "volume_ml": 250, "collection_date": today - timedelta(days=20), "expiry_date": today + timedelta(days=345), "storage_location": "Ultra-Cold Freezer -30C", "status": "In Storage"},
            {"id": "3", "unit_number": "LS-UNIT-2026-0003", "blood_group": "A+", "donor_id": "7", "donation_id": "3", "component_type": "Packed Red Blood Cells", "volume_ml": 450, "collection_date": today - timedelta(days=5), "expiry_date": today + timedelta(days=30), "storage_location": "Vault A, Shelf 2", "status": "In Storage"},
            {"id": "4", "unit_number": "LS-UNIT-2026-0004", "blood_group": "B+", "donor_id": "8", "donation_id": "4", "component_type": "Whole Human Blood", "volume_ml": 500, "collection_date": today - timedelta(days=30), "expiry_date": today + timedelta(days=5), "storage_location": "Vault B, Shelf 1", "status": "In Storage"},
            {"id": "5", "unit_number": "LS-UNIT-2026-0005", "blood_group": "O-", "donor_id": "10", "donation_id": "5", "component_type": "Packed Red Blood Cells", "volume_ml": 450, "collection_date": today - timedelta(days=12), "expiry_date": today + timedelta(days=23), "storage_location": "Vault A, Emergency Shelf", "status": "In Storage"},
            {"id": "6", "unit_number": "LS-UNIT-2026-0006", "blood_group": "O-", "donor_id": "10", "donation_id": "6", "component_type": "Platelets", "volume_ml": 300, "collection_date": today - timedelta(days=2), "expiry_date": today + timedelta(days=3), "storage_location": "Agitator Incubator 22C", "status": "In Storage"},
            {"id": "7", "unit_number": "LS-UNIT-2026-0007", "blood_group": "A-", "donor_id": "11", "donation_id": "7", "component_type": "Packed Red Blood Cells", "volume_ml": 450, "collection_date": today - timedelta(days=8), "expiry_date": today + timedelta(days=27), "storage_location": "Vault B, Shelf 2", "status": "In Storage"},
            {"id": "8", "unit_number": "LS-UNIT-2026-0008", "blood_group": "B-", "donor_id": "12", "donation_id": "8", "component_type": "Packed Red Blood Cells", "volume_ml": 450, "collection_date": today - timedelta(days=15), "expiry_date": today + timedelta(days=20), "storage_location": "Vault B, Rare Shelf", "status": "In Storage"},
            {"id": "9", "unit_number": "LS-UNIT-2026-0009", "blood_group": "AB-", "donor_id": "13", "donation_id": "9", "component_type": "Packed Red Blood Cells", "volume_ml": 450, "collection_date": today - timedelta(days=6), "expiry_date": today + timedelta(days=29), "storage_location": "Vault B, Rare Shelf", "status": "In Storage"},
            {"id": "10", "unit_number": "LS-UNIT-2026-0010", "blood_group": "O-", "donor_id": "10", "donation_id": None, "component_type": "Packed Red Blood Cells", "volume_ml": 450, "collection_date": today - timedelta(days=18), "expiry_date": today + timedelta(days=17), "storage_location": "Vault A, Emergency Shelf", "status": "Issued", "issued_to_hospital_id": "5", "issued_at": datetime.now(timezone.utc) - timedelta(days=2)},
            {"id": "11", "unit_number": "LS-UNIT-2026-0011", "blood_group": "O-", "donor_id": "10", "donation_id": None, "component_type": "Packed Red Blood Cells", "volume_ml": 450, "collection_date": today - timedelta(days=18), "expiry_date": today + timedelta(days=17), "storage_location": "Vault A, Emergency Shelf", "status": "Issued", "issued_to_hospital_id": "5", "issued_at": datetime.now(timezone.utc) - timedelta(days=2)},
            {"id": "12", "unit_number": "LS-UNIT-2026-0012", "blood_group": "AB+", "donor_id": "9", "donation_id": None, "component_type": "Fresh Frozen Plasma", "volume_ml": 250, "collection_date": today - timedelta(days=14), "expiry_date": today + timedelta(days=350), "storage_location": "Ultra-Cold Freezer -30C", "status": "Issued", "issued_to_hospital_id": "2", "issued_at": datetime.now(timezone.utc) - timedelta(days=3)},
            {"id": "13", "unit_number": "LS-UNIT-2026-0013", "blood_group": "B+", "donor_id": "8", "donation_id": None, "component_type": "Packed Red Blood Cells", "volume_ml": 450, "collection_date": today - timedelta(days=38), "expiry_date": today - timedelta(days=3), "storage_location": "Quarantine Bio-Waste Bin", "status": "Expired"},
            {"id": "14", "unit_number": "LS-UNIT-2026-0014", "blood_group": "A+", "donor_id": "7", "donation_id": None, "component_type": "Packed Red Blood Cells", "volume_ml": 450, "collection_date": today - timedelta(days=3), "expiry_date": today + timedelta(days=32), "storage_location": "Vault A, Shelf 2", "status": "Reserved"},
            {"id": "15", "unit_number": "LS-UNIT-2026-0015", "blood_group": "O+", "donor_id": "6", "donation_id": None, "component_type": "Platelets", "volume_ml": 300, "collection_date": today - timedelta(days=1), "expiry_date": today + timedelta(days=4), "storage_location": "Agitator Incubator 22C", "status": "In Storage"}
        ]
        for u in units_data:
            unit = BloodBagUnit.get(u["id"])
            if not unit:
                unit = BloodBagUnit(**u)
                unit.save()
        print(f"[OK] {len(units_data)} Sterile Blood Bag Units created with QR code credentials.")

        # -------------------------------------------------------------
        # 9. Emergency Alert Logs
        # -------------------------------------------------------------
        alerts_data = [
            {
                "id": "1",
                "request_id": "1",
                "donor_id": "6",
                "channel": "SMS",
                "recipient_contact": "+1 555-0201",
                "status": "Delivered",
                "message_content": "URGENT LIFE SAVER ALERT: City General Hospital has raised an EMERGENCY requisition for 4 unit(s) of O+ blood. You are a compatible eligible donor nearby.",
                "sent_at": datetime.now(timezone.utc) - timedelta(hours=2)
            },
            {
                "id": "2",
                "request_id": "1",
                "donor_id": "6",
                "channel": "Email",
                "recipient_contact": "john.doe@email.com",
                "status": "Delivered",
                "message_content": "URGENT LIFE SAVER ALERT: City General Hospital has raised an EMERGENCY requisition for 4 unit(s) of O+ blood. You are a compatible eligible donor nearby.",
                "sent_at": datetime.now(timezone.utc) - timedelta(hours=2)
            },
            {
                "id": "3",
                "request_id": "1",
                "donor_id": "10",
                "channel": "SMS",
                "recipient_contact": "+1 555-0205",
                "status": "Delivered",
                "message_content": "URGENT LIFE SAVER ALERT: City General Hospital has raised an EMERGENCY requisition for 4 unit(s) of O+ blood. You are an eligible universal donor nearby.",
                "sent_at": datetime.now(timezone.utc) - timedelta(hours=2)
            },
            {
                "id": "4",
                "request_id": "2",
                "donor_id": "11",
                "channel": "SMS",
                "recipient_contact": "+1 555-0206",
                "status": "Delivered",
                "message_content": "URGENT LIFE SAVER ALERT: St. Jude Trauma Center has raised a CRITICAL requisition for 2 unit(s) of A- blood. You are a compatible eligible donor.",
                "sent_at": datetime.now(timezone.utc) - timedelta(hours=5)
            }
        ]
        for a in alerts_data:
            alert = EmergencyAlert.get(a["id"])
            if not alert:
                alert = EmergencyAlert(**a)
                alert.save()
        print(f"[OK] {len(alerts_data)} Emergency alert notification logs created.")

        print("\n[SUCCESS] Firebase database seeding completed successfully!")
        print("-------------------------------------------------------")
        print("Demo Credentials:")
        print(" * Administrator: admin@bloodbank.org / Admin@123")
        print(" * Hospital:      citygeneral@hospital.org / Hospital@123")
        print(" * Donor:         john.doe@email.com / Donor@123")
        print("-------------------------------------------------------")

if __name__ == '__main__':
    seed_firebase()
