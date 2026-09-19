from datetime import date, datetime, timedelta, timezone
from app import create_app, db
from app.models import (
    User, DonorProfile, HospitalProfile, BloodInventory,
    BloodRequest, DonationRecord, DonationCamp,
    BloodBagUnit, EmergencyAlert
)

def seed_database():
    app = create_app()
    with app.app_context():
        # Create all tables if they don't exist
        db.create_all()

        # Check if already seeded
        if User.query.filter_by(role='admin').first():
            print("Database already contains records. Skipping initial seeding.")
            return

        print("Seeding Blood Bank Management System with demo data...")

        # 1. Seed Blood Inventory (All 8 Groups)
        inventory_data = [
            ('A+', 18, 5),
            ('A-', 6, 5),
            ('B+', 15, 5),
            ('B-', 4, 5),   # Critical
            ('AB+', 10, 4),
            ('AB-', 3, 4),   # Critical
            ('O+', 24, 6),
            ('O-', 5, 5),   # Critical
        ]
        for bg, units, thresh in inventory_data:
            inv = BloodInventory(blood_group=bg, units_available=units, critical_threshold=thresh)
            db.session.add(inv)
        db.session.commit()
        print(" Blood Inventory initialized (8 blood groups).")

        # 2. Seed Admin
        admin = User(
            name="Chief Medical Administrator",
            email="admin@bloodbank.org",
            role="admin",
            phone="+1 (800) 555-0100",
            city="Metropolis",
            address="742 Central Blood Repository Blvd"
        )
        admin.set_password("Admin@123")
        db.session.add(admin)
        db.session.commit()
        print(" Admin account created: admin@bloodbank.org / Admin@123")

        # 3. Seed Hospitals
        hospitals_data = [
            {
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
                "name": "Memorial Heart & Surgical Institute",
                "email": "memorial@hospital.org",
                "phone": "+1 555-0114",
                "city": "Central City",
                "address": "520 Cardiology Way",
                "license": "HOSP-SURG-7742",
                "type": "Government Medical Center",
                "emergency": "+1 555-9114"
            }
        ]

        hospital_users = []
        for h_data in hospitals_data:
            user = User(
                name=h_data["name"],
                email=h_data["email"],
                role="hospital",
                phone=h_data["phone"],
                city=h_data["city"],
                address=h_data["address"]
            )
            user.set_password("Hospital@123")
            db.session.add(user)
            db.session.flush()

            h_prof = HospitalProfile(
                user_id=user.id,
                license_number=h_data["license"],
                hospital_type=h_data["type"],
                emergency_contact=h_data["emergency"],
                is_verified=True
            )
            db.session.add(h_prof)
            hospital_users.append(user)
        db.session.commit()
        print(f" {len(hospital_users)} partner hospitals seeded.")

        # 4. Seed Donation Camps
        camps_data = [
            {
                "title": "Metropolis Downtown Annual Blood Drive",
                "organized_by": "Rotary Club & Red Cross",
                "location": "City Convention Center, Hall B",
                "city": "Metropolis",
                "date": date.today() + timedelta(days=5),
                "start": "09:00 AM",
                "end": "05:00 PM",
                "person": "Dr. Sarah Miller",
                "phone": "+1 555-0182",
                "desc": "Join our largest annual mobile drive. Free health screening, refreshments, and commemorative donor pins provided."
            },
            {
                "title": "Gotham University Campus Blood Drive",
                "organized_by": "Gotham Youth Volunteers",
                "location": "Student Activity Center Plaza",
                "city": "Gotham City",
                "date": date.today() + timedelta(days=12),
                "start": "10:00 AM",
                "end": "04:00 PM",
                "person": "Prof. Alan Wayne",
                "phone": "+1 555-0188",
                "desc": "Open to all students, faculty, and public neighbors. Help replenish emergency trauma reserves."
            },
            {
                "title": "Star City Corporate Park Donation Drive",
                "organized_by": "Star City Tech Alliance",
                "location": "Tech Hub Quad, Building 4",
                "city": "Star City",
                "date": date.today() + timedelta(days=18),
                "start": "08:30 AM",
                "end": "03:30 PM",
                "person": "Elena Vance",
                "phone": "+1 555-0195",
                "desc": "Mobile phlebotomy vans on site with temperature-controlled beds and certified medical staff."
            }
        ]

        camps = []
        for c_data in camps_data:
            camp = DonationCamp(
                title=c_data["title"],
                organized_by=c_data["organized_by"],
                location=c_data["location"],
                city=c_data["city"],
                camp_date=c_data["date"],
                start_time=c_data["start"],
                end_time=c_data["end"],
                contact_person=c_data["person"],
                contact_phone=c_data["phone"],
                description=c_data["desc"],
                status="Upcoming"
            )
            db.session.add(camp)
            camps.append(camp)
        db.session.commit()
        print(f" {len(camps)} upcoming donation camps scheduled.")

        # 5. Seed Donors
        donors_data = [
            {
                "name": "John Doe",
                "email": "john.doe@email.com",
                "phone": "+1 555-0199",
                "city": "Metropolis",
                "address": "12 Elm St, Apt 4B",
                "blood_group": "O+",
                "gender": "Male",
                "age": 29,
                "weight": 76.5,
                "last_donation": date.today() - timedelta(days=105),  # Eligible!
                "notes": "Regular whole blood donor. No known allergies."
            },
            {
                "name": "Sarah Connor",
                "email": "sarah.c@email.com",
                "phone": "+1 555-0201",
                "city": "Gotham City",
                "address": "88 Industrial Way",
                "blood_group": "A+",
                "gender": "Female",
                "age": 34,
                "weight": 62.0,
                "last_donation": date.today() - timedelta(days=40),  # In cooldown
                "notes": "Platelet donor candidate."
            },
            {
                "name": "Michael Chang",
                "email": "michael.chang@email.com",
                "phone": "+1 555-0202",
                "city": "Metropolis",
                "address": "320 Oak Ridge Ave",
                "blood_group": "B+",
                "gender": "Male",
                "age": 42,
                "weight": 81.0,
                "last_donation": date.today() - timedelta(days=130),  # Eligible!
                "notes": "Universal plasma donor."
            },
            {
                "name": "Emily Davis",
                "email": "emily.davis@email.com",
                "phone": "+1 555-0203",
                "city": "Star City",
                "address": "15 Maple Lane",
                "blood_group": "O-",  # Universal red cell donor!
                "gender": "Female",
                "age": 27,
                "weight": 58.5,
                "last_donation": date.today() - timedelta(days=15),  # In cooldown
                "notes": "Universal O-negative heroic donor."
            },
            {
                "name": "Robert Taylor",
                "email": "robert.t@email.com",
                "phone": "+1 555-0204",
                "city": "Central City",
                "address": "402 Pine Terrace",
                "blood_group": "AB+",
                "gender": "Male",
                "age": 38,
                "weight": 84.0,
                "last_donation": None,  # First time donor!
                "notes": "Universal recipient group."
            },
            {
                "name": "Jessica Miller",
                "email": "jessica.m@email.com",
                "phone": "+1 555-0205",
                "city": "Gotham City",
                "address": "90 Cedar Street",
                "blood_group": "A-",
                "gender": "Female",
                "age": 31,
                "weight": 60.0,
                "last_donation": date.today() - timedelta(days=95),  # Eligible!
                "notes": "Healthy donor, Rh negative."
            },
            {
                "name": "David Wilson",
                "email": "david.w@email.com",
                "phone": "+1 555-0206",
                "city": "Metropolis",
                "address": "77 Willow Lane",
                "blood_group": "B-",
                "gender": "Male",
                "age": 45,
                "weight": 79.0,
                "last_donation": date.today() - timedelta(days=200),  # Eligible!
                "notes": "Rare blood group."
            },
            {
                "name": "Amanda White",
                "email": "amanda.white@email.com",
                "phone": "+1 555-0207",
                "city": "Star City",
                "address": "610 Riverbank Dr",
                "blood_group": "AB-",
                "gender": "Female",
                "age": 26,
                "weight": 55.0,
                "last_donation": None,  # First time donor!
                "notes": "Rare AB-negative donor."
            }
        ]

        donor_users = []
        for d_data in donors_data:
            user = User(
                name=d_data["name"],
                email=d_data["email"],
                role="donor",
                phone=d_data["phone"],
                city=d_data["city"],
                address=d_data["address"]
            )
            user.set_password("Donor@123")
            db.session.add(user)
            db.session.flush()

            d_prof = DonorProfile(
                user_id=user.id,
                blood_group=d_data["blood_group"],
                gender=d_data["gender"],
                age=d_data["age"],
                weight=d_data["weight"],
                last_donation_date=d_data["last_donation"],
                medical_notes=d_data["notes"]
            )
            db.session.add(d_prof)
            donor_users.append(user)
        db.session.commit()
        print(f" {len(donor_users)} registered donors seeded.")

        # 6. Seed Past Donation Records
        donations_to_seed = [
            {
                "donor": donor_users[0],  # John Doe (O+)
                "date": date.today() - timedelta(days=105),
                "units": 1,
                "bg": "O+",
                "camp": None,
                "verified": "Chief Medical Administrator",
                "notes": "Standard donation, vitals normal."
            },
            {
                "donor": donor_users[0],  # John Doe (O+)
                "date": date.today() - timedelta(days=210),
                "units": 1,
                "bg": "O+",
                "camp": None,
                "verified": "Chief Medical Administrator",
                "notes": "Central blood bank collection."
            },
            {
                "donor": donor_users[1],  # Sarah Connor (A+)
                "date": date.today() - timedelta(days=40),
                "units": 1,
                "bg": "A+",
                "camp": None,
                "verified": "Dr. Sarah Miller",
                "notes": "Quick painless phlebotomy."
            },
            {
                "donor": donor_users[2],  # Michael Chang (B+)
                "date": date.today() - timedelta(days=130),
                "units": 1,
                "bg": "B+",
                "camp": None,
                "verified": "Chief Medical Administrator",
                "notes": "Completed donation, donor was well hydrated."
            },
            {
                "donor": donor_users[3],  # Emily Davis (O-)
                "date": date.today() - timedelta(days=15),
                "units": 1,
                "bg": "O-",
                "camp": None,
                "verified": "Chief Medical Administrator",
                "notes": "Urgent universal donor intake."
            }
        ]

        for d_rec in donations_to_seed:
            record = DonationRecord(
                donor_id=d_rec["donor"].id,
                camp_id=d_rec["camp"].id if d_rec["camp"] else None,
                blood_group=d_rec["bg"],
                units_donated=d_rec["units"],
                donation_date=d_rec["date"],
                status="Completed",
                verified_by=d_rec["verified"],
                notes=d_rec["notes"]
            )
            db.session.add(record)
        db.session.commit()
        print(f" {len(donations_to_seed)} past donation records seeded.")

        # 7. Seed Hospital Blood Requisitions
        sample_requests = [
            {
                "hospital": hospital_users[0],  # City General Hospital
                "blood_group": "O+",
                "units": 3,
                "urgency": "Emergency",
                "patient": "Marcus Vance",
                "case_no": "MRN-2026-1049",
                "reason": "Multitrauma road accident casualty; multiple fractures & internal bleeding.",
                "status": "Pending",
                "notes": None
            },
            {
                "hospital": hospital_users[1],  # St. Jude Trauma Center
                "blood_group": "A+",
                "units": 2,
                "urgency": "Critical",
                "patient": "Clara Oswald",
                "case_no": "MRN-2026-8831",
                "reason": "Emergency abdominal aortic aneurysm surgery scheduled in 2 hours.",
                "status": "Approved",
                "notes": "Approved. Packed in cold box #3 with dry refrigerant."
            },
            {
                "hospital": hospital_users[2],  # Metro Children's Clinic
                "blood_group": "B+",
                "units": 1,
                "urgency": "Normal",
                "patient": "Lucas Smith",
                "case_no": "PED-2026-041",
                "reason": "Severe sickle cell anemia crisis with acute chest syndrome.",
                "status": "Dispensed",
                "notes": "Dispensed to hospital courier at 08:30 AM."
            },
            {
                "hospital": hospital_users[3],  # Memorial Heart & Surgical
                "blood_group": "O-",
                "units": 2,
                "urgency": "Emergency",
                "patient": "Eleanor Rigby",
                "case_no": "SURG-2026-559",
                "reason": "Open heart bypass surgery; universal red cell compatibility essential.",
                "status": "Pending",
                "notes": None
            }
        ]

        for req in sample_requests:
            br = BloodRequest(
                hospital_id=req["hospital"].id,
                blood_group=req["blood_group"],
                units_requested=req["units"],
                urgency=req["urgency"],
                patient_name=req["patient"],
                patient_case_no=req["case_no"],
                reason=req["reason"],
                status=req["status"],
                admin_notes=req["notes"],
                created_at=datetime.now(timezone.utc) - timedelta(hours=3 if req["status"] == "Pending" else 24)
            )
            db.session.add(br)
        db.session.commit()
        print(f" {len(sample_requests)} sample hospital requisitions seeded.")

        # 8. Seed Individual Blood Bag Units with QR Data
        sample_bags = [
            {
                "unit_number": "LS-UNIT-2026-0001",
                "blood_group": "O+",
                "donor_id": donor_users[0].id,
                "component": "Packed Red Blood Cells",
                "volume": 450,
                "days_ago": 5,
                "shelf_life": 35,
                "vault": "Cold Vault Compartment A1",
                "status": "In Storage"
            },
            {
                "unit_number": "LS-UNIT-2026-0002",
                "blood_group": "O-",
                "donor_id": donor_users[3].id,
                "component": "Packed Red Blood Cells",
                "volume": 450,
                "days_ago": 2,
                "shelf_life": 35,
                "vault": "Cold Vault Compartment A2",
                "status": "In Storage"
            },
            {
                "unit_number": "LS-UNIT-2026-0003",
                "blood_group": "A+",
                "donor_id": donor_users[1].id,
                "component": "Whole Human Blood",
                "volume": 450,
                "days_ago": 12,
                "shelf_life": 35,
                "vault": "Cold Vault Compartment B1",
                "status": "Reserved"
            },
            {
                "unit_number": "LS-UNIT-2026-0004",
                "blood_group": "B+",
                "donor_id": donor_users[2].id,
                "component": "Fresh Frozen Plasma",
                "volume": 250,
                "days_ago": 20,
                "shelf_life": 365,
                "vault": "Deep Freeze Compartment F1",
                "status": "Issued"
            },
            {
                "unit_number": "LS-UNIT-2026-0005",
                "blood_group": "AB+",
                "donor_id": donor_users[4].id,
                "component": "Platelet Concentrate",
                "volume": 300,
                "days_ago": 3,
                "shelf_life": 7,
                "vault": "Platelet Agitator Vault C",
                "status": "In Storage"
            }
        ]

        for bag in sample_bags:
            coll_date = date.today() - timedelta(days=bag["days_ago"])
            exp_date = coll_date + timedelta(days=bag["shelf_life"])
            b_unit = BloodBagUnit(
                unit_number=bag["unit_number"],
                blood_group=bag["blood_group"],
                donor_id=bag["donor_id"],
                component_type=bag["component"],
                volume_ml=bag["volume"],
                collection_date=coll_date,
                expiry_date=exp_date,
                storage_location=bag["vault"],
                status=bag["status"],
                screening_results="HIV: Non-Reactive | HBV: Non-Reactive | HCV: Non-Reactive | Syphilis: Non-Reactive"
            )
            if bag["status"] == "Issued":
                b_unit.issued_to_hospital_id = hospital_users[0].id
                b_unit.issued_at = datetime.now(timezone.utc) - timedelta(days=1)
            db.session.add(b_unit)
        db.session.commit()
        print(f" {len(sample_bags)} sterile blood bags with QR tracking generated.")

        # 9. Seed Sample Emergency Alerts
        req1 = BloodRequest.query.filter_by(blood_group="O+").first()
        if req1:
            alert = EmergencyAlert(
                request_id=req1.id,
                donor_id=donor_users[0].id,  # John Doe (O+)
                channel="SMS",
                recipient_contact=donor_users[0].phone,
                status="Delivered",
                message_content=f"URGENT LIFE SAVER ALERT: City General Hospital needs O+ blood for emergency surgery. You are a compatible eligible donor nearby.",
                sent_at=datetime.now(timezone.utc) - timedelta(hours=2)
            )
            db.session.add(alert)
            db.session.commit()
            print(" Sample emergency donor broadcast alert seeded.")

        print("\n Seeding completed successfully!")
        print("\nDefault Credentials:")
        print("-----------------------------------------------------------------")
        print(" ADMIN:    admin@bloodbank.org         / Admin@123")
        print(" HOSPITAL: citygeneral@hospital.org    / Hospital@123")
        print(" DONOR:    john.doe@email.com          / Donor@123")
        print("-----------------------------------------------------------------")

if __name__ == '__main__':
    seed_database()
