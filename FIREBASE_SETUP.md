# Life Saver - Firebase Database Setup & Integration Guide

Welcome to **Life Saver**! The entire backend is built to use **Google Cloud Firebase (Firestore)** as its primary database.

---

## ⚡ Quick Start: Dual Mode Architecture

Life Saver includes a smart **Dual-Mode Firebase Engine**:

1. **🚀 Local Firestore Mode (Zero-Config, Default)**:
   - When no external Firebase credentials file is present, the app automatically runs in **Local Firestore Mode**.
   - It maintains full compatibility with the official Google Cloud Firestore Python SDK (`firebase_admin.firestore`) and persists all collections to `firebase_db_data.json`.
   - **You can immediately launch and test the app with `python run.py` without needing a Google Cloud account!**

2. **🔥 Live Google Cloud Firebase Mode (Production Ready)**:
   - As soon as you place your `serviceAccountKey.json` into the project root (or point `FIREBASE_CREDENTIALS` to it), Life Saver automatically switches to **Live Google Cloud Firebase Firestore**.

---

## 🛠️ Step-by-Step: Connecting to Your Live Firebase Project

If you want to connect Life Saver to your live Google Firebase Console:

### Step 1: Create a Project in Firebase Console
1. Navigate to the [Firebase Console](https://console.firebase.google.com/).
2. Click **Add project** (or **Create a project**).
3. Name your project (e.g. `lifesaver-bloodbank`) and click **Continue**.
4. (Optional) Disable or enable Google Analytics, then click **Create Project**.

### Step 2: Enable Cloud Firestore
1. In the left navigation menu of the Firebase console, go to **Build** > **Firestore Database**.
2. Click **Create database**.
3. Choose a location closest to your users (e.g., `nam5 (us-central)` or `asia-south1`).
4. Select **Start in test mode** for development (or production mode with the rules below), and click **Enable**.

### Step 3: Download your Service Account Private Key
1. In the Firebase console, click the gear icon ⚙️ next to **Project Overview** in the left sidebar and choose **Project settings**.
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
