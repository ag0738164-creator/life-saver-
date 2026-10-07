# Life Saver - Firebase Database Setup & Integration Guide

Welcome to **Life Saver**! The entire backend is built to use **Google Cloud Firebase (Firestore)** as its primary database.

---

## ⚡ Quick Start: Dual Mode Architecture & Active Project

Your project **`lifesaver-2df25`** is configured and active!

```javascript
const firebaseConfig = {
  apiKey: "AIzaSyDjJ8NA1ipMnuBBSfU6GJ7kA48kU0m6_5g",
  authDomain: "lifesaver-2df25.firebaseapp.com",
  projectId: "lifesaver-2df25",
  storageBucket: "lifesaver-2df25.firebasestorage.app",
  messagingSenderId: "963027586131",
  appId: "1:963027586131:web:2b129ae969107cca050aa6"
};
```

Life Saver includes a smart **Dual-Mode Firebase Engine**:

1. **🚀 Local Firestore Mode (Zero-Config, Default)**:
   - When no external Firebase service account credentials file is present, the app automatically runs in **Local Firestore Mode**.
   - It maintains full compatibility with the official Google Cloud Firestore Python SDK (`firebase_admin.firestore`) and persists all collections to `firebase_db_data.json`.
   - The Web SDK is initialized on the frontend with your `lifesaver-2df25` project configuration.
   - **You can immediately launch and test the app with `python run.py`!**

2. **🔥 Live Google Cloud Firebase Mode (Production Ready)**:
   - To connect the Python backend directly to your live Cloud Firestore for project `lifesaver-2df25`, generate and download the Service Account Private Key from Firebase Console and place it as `serviceAccountKey.json` in the root folder.
   - Life Saver will automatically detect it and switch backend operations to **Live Google Cloud Firebase Firestore**.

---

## 🛠️ Step-by-Step: Connecting Backend Directly to `lifesaver-2df25`

### Step 1: Enable Cloud Firestore in `lifesaver-2df25`
1. Navigate to the [Firebase Console](https://console.firebase.google.com/) and open **`lifesaver-2df25`**.
2. In the left navigation menu, go to **Build** > **Firestore Database**.
3. Click **Create database** (if not created already).
4. Select a location and mode (**Start in test mode** for development), and click **Enable**.

### Step 2: Download your Service Account Private Key
1. In the Firebase console for `lifesaver-2df25`, click the gear icon ⚙️ next to **Project Overview** in the left sidebar and choose **Project settings**.
2. Go to the **Service accounts** tab.
3. Verify that **Python** is selected.
4. Click the **Generate new private key** button, and confirm by clicking **Generate key**.
5. A JSON file will download to your computer.
6. Rename this file to `serviceAccountKey.json` and move it directly into the root folder of this project:
   ```text
   blood_bank_management_system/
   ├── serviceAccountKey.json  <--- Place here!
   ├── run.py
   ├── seed_firebase.py
   ...
   ```

### Step 4: Seed Initial Data into Live Firestore
Once `serviceAccountKey.json` is in place, populate all master collections with demo hospitals, donors, inventory, and sterile blood units by running:
```powershell
python seed_firebase.py
```
You will see:
```text
[Firebase] Connected to Live Google Cloud Firebase Firestore via .../serviceAccountKey.json
[Firebase] Initializing Firebase Seeding in mode: [live_firebase]
[OK] Blood Inventory initialized (8 blood groups).
[OK] Admin account initialized: admin@bloodbank.org / Admin@123
[OK] 4 Hospitals registered & verified.
[OK] 8 Donors registered with medical eligibility profiles.
[OK] 4 Donation Camps scheduled.
[OK] 10 Donation history records seeded.
[OK] 7 Hospital blood requisitions initialized.
[OK] 15 Sterile Blood Bag Units created with QR code credentials.
[OK] 4 Emergency alert notification logs created.
[SUCCESS] Firebase database seeding completed successfully!
```

### Step 5: Start the Application
Run the Flask server:
```powershell
python run.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser.

---

## 🗄️ Firestore Collections Structure

| Collection Name | Document ID | Description |
|---|---|---|
| `users` | User ID (`1`, `2`, ...) | Authentication, role (`admin`, `donor`, `hospital`), contact & address |
| `donor_profiles` | User ID | Blood group, age, weight, last donation date, cooldown status |
| `hospital_profiles` | User ID | License number, hospital classification, emergency contact |
| `blood_inventory` | Blood Group (`A+`, `O-`, ...) | Units available, critical safe threshold, last updated timestamp |
| `blood_requests` | Request ID | Requisition details, urgency (`Normal`, `Critical`, `Emergency`), status |
| `blood_bag_units` | Unit ID | Barcode/QR number (`LS-UNIT-2026-XXXX`), sterile test results, expiry |
| `donation_camps` | Camp ID | Title, city, location, dates, organizer |
| `donation_records` | Record ID | Donor donation history, units donated, verification notes |
| `emergency_alerts` | Alert ID | Dispatched SMS and Email logs with delivery timestamps |

---

## 🔒 Recommended Firestore Security Rules

When transitioning to production, navigate to **Firestore Database** > **Rules** and apply:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Admin SDK bypasses security rules on the server side.
    // Client web-read rules:
    match /blood_inventory/{group} {
      allow read: if true;
      allow write: if false; // Only server backend writes
    }
    match /donation_camps/{campId} {
      allow read: if true;
      allow write: if false;
    }
    match /{document=**} {
      allow read, write: if false; // All other collections mediated by Flask backend
    }
  }
}
```

---

## 🧪 Verification & Automated Testing

Run the full automated test suite anytime:
```powershell
# Run all tests
python -m unittest discover -s tests -v

# Run dedicated Firebase tests
python -m unittest tests/test_firebase.py -v
```
