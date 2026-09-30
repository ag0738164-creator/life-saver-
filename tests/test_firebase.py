import os
import unittest
from datetime import datetime, date, timezone
from config import Config
from app import create_app, db
from app.firebase_db import get_firebase_db, LocalFirestoreDB, get_db_mode
from app.models import (
    User, DonorProfile, HospitalProfile, BloodInventory,
    BloodRequest, DonationCamp, DonationRecord, BloodBagUnit, EmergencyAlert
)
from seed_firebase import seed_firebase

TEST_FIREBASE_PATH = os.path.join(os.path.dirname(__file__), 'test_firestore_db.json')

class TestFirebaseConfig(Config):
    TESTING = True
    LOCAL_FIRESTORE_PATH = TEST_FIREBASE_PATH
    WTF_CSRF_ENABLED = False

class FirebaseIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_FIREBASE_PATH):
            try:
                os.remove(TEST_FIREBASE_PATH)
            except Exception:
                pass
        self.app = create_app(TestFirebaseConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.firestore = get_firebase_db(self.app.config)

    def tearDown(self):
        self.app_context.pop()
        if os.path.exists(TEST_FIREBASE_PATH):
            try:
                os.remove(TEST_FIREBASE_PATH)
            except Exception:
                pass

    def test_direct_firestore_document_operations(self):
        """Test direct Firestore collection and document CRUD operations."""
        col = self.firestore.collection('test_items')
        
        # 1. Create document
        doc_ref = col.document('item_1')
        doc_ref.set({'name': 'Plasma Separator', 'status': 'Operational', 'count': 4})
        
        # 2. Read document
        snap = doc_ref.get()
        self.assertTrue(snap.exists)
        data = snap.to_dict()
        self.assertEqual(data['name'], 'Plasma Separator')
        self.assertEqual(data['count'], 4)

        # 3. Update document
        doc_ref.update({'count': 5, 'last_checked': '2026-09-30'})
        updated_snap = doc_ref.get()
        self.assertEqual(updated_snap.to_dict()['count'], 5)
        self.assertEqual(updated_snap.to_dict()['last_checked'], '2026-09-30')

        # 4. Stream & Query
        doc_ref2 = col.document('item_2')
        doc_ref2.set({'name': 'Refrigerated Centrifuge', 'status': 'Maintenance', 'count': 2})

        query_results = list(col.where('status', '==', 'Operational').stream())
        self.assertEqual(len(query_results), 1)
        self.assertEqual(query_results[0].to_dict()['name'], 'Plasma Separator')

        # 5. Delete document
        doc_ref.delete()
        self.assertFalse(doc_ref.get().exists)

    def test_firebase_model_persistence(self):
        """Test domain models persisting to Firestore collections."""
        # Create and save a user
        u = User(
            name="Firebase Test Admin",
            email="fb_admin@lifesaver.org",
            role="admin",
            phone="+1 555-0999"
        )
        u.set_password("AdminSecurePass!1")
        u.save()

        fetched_user = User.query.filter_by(email="fb_admin@lifesaver.org").first()
        self.assertIsNotNone(fetched_user)
        self.assertEqual(fetched_user.name, "Firebase Test Admin")
        self.assertTrue(fetched_user.check_password("AdminSecurePass!1"))
        self.assertTrue(fetched_user.is_admin)

        # Create and save inventory
        inv = BloodInventory(
            id="O+",
            blood_group="O+",
            units_available=25,
            critical_threshold=6
        )
        inv.save()

        fetched_inv = BloodInventory.get("O+")
        self.assertIsNotNone(fetched_inv)
        self.assertEqual(fetched_inv.units_available, 25)
        self.assertEqual(fetched_inv.status_label, "Sufficient")

    def test_firebase_seeder_execution(self):
        """Test that the Firebase seeder correctly creates all core collections."""
        seed_firebase()

        # Check users count (1 admin + 4 hospitals + 8 donors = 13 users)
        total_users = User.query.count()
        self.assertGreaterEqual(total_users, 13)

        # Check inventory (8 blood groups)
        inventory_items = BloodInventory.query.all()
        self.assertEqual(len(inventory_items), 8)

        # Check blood bags
        bags = BloodBagUnit.query.all()
        self.assertGreaterEqual(len(bags), 15)

        # Check requests
        requests = BloodRequest.query.all()
        self.assertGreaterEqual(len(requests), 7)

        # Check QR codes can be generated from seeded blood bags
        first_bag = bags[0]
        qr_uri = first_bag.get_qr_image()
        self.assertTrue(qr_uri.startswith('data:image/png;base64,'))

if __name__ == '__main__':
    unittest.main()
