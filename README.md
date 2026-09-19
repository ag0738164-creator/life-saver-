# Life Saver - Intelligent Blood Bank & Transfusion Logistics Network

**Life Saver** is an intelligent, centralized, and responsive healthcare web platform designed to automate blood donor management, maintain real-time cold-chain inventory, and streamline hospital blood requisitions to eliminate delays during medical emergencies.

Developed using **Python (Flask)**, **Bootstrap 5**, **Chart.js**, and **SQLAlchemy (SQLite3 / MySQL)**.

---

##  Advanced Features

### 1. AI-Based Blood Demand Prediction
- **Multi-Factor Machine Learning Time-Series Engine**:
  - Analyzes historical hospital requisition velocity, clinical emergency pull rates, population blood-group prevalence, and seasonal multipliers.
  - Generates **14-day** and **30-day** blood unit requirement forecasts across all 8 major groups (`A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `O+`, `O-`).
  - Flags **Deficit Risk Levels** (`Critical Shortage Risk`, `Moderate Deficit Warning`, `Stable / Balanced`, `Optimal Reserve`) comparing forecasted demand directly against cold-chain storage.
  - Actionable AI directives: Recommends targeted donor calls and scheduling mobile blood drives before anticipated shortages hit.
  - Interactive **Chart.js comparative visualization** of Current In-Vault Stock vs. AI-Forecasted Demand.

### 2. Location-Based Emergency Donor Matching
- **Geo-Proximity & Compatibility Engine**:
  - When an emergency blood requisition is raised by a hospital, the system instantly calculates **ABO/Rh red cell compatibility** (`O-` universal red cell donor, `AB+` universal recipient, Rh-negative rules).
  - Matches active registered donors located in the same city or neighboring proximity.
  - Strictly filters by medical eligibility: verifies that the mandatory **90-day cooldown period** has elapsed, donor age is 18-65, and weight &ge; 50 kg.
  - **Instant Alert Dispatcher**: Broadcasts simulated SMS and Email emergency notifications to matched donors with 1-click appeal notifications.

### 3. QR Code-Based Blood Unit Tracking
- **Sterile Bag Lifecycle Management**:
  - Every collected blood unit is assigned a unique tracking identifier (e.g. `LS-UNIT-2026-0001`) and a cryptographic **Base64 QR code**.
  - Encodes blood group, component type (*Packed Red Blood Cells*, *Whole Blood*, *Platelets*, *Fresh Frozen Plasma*), volume, collection date, expiry date, storage location, and serological screening clearance (HIV, HBV, HCV, Syphilis: Non-Reactive).
  - **Interactive QR & Barcode Scanner**: Scan or enter unit numbers to verify safety screening, check remaining shelf life, quarantine, or issue units to hospitals.
  - **Printable Transfusion Bag Labels**: Generates standardized ISBT-128 sterile bag adhesive labels with barcodes and scannable QR tags.

---

## Core System Features

- **Role-Based Access Control (RBAC)**: Dedicated secure portals for **Administrators**, **Blood Donors**, and **Hospitals**.
- **Dynamic Inventory Consistency**: 
  - Units automatically decrement upon administrative approval and dispatch of hospital requisitions.
  - Units automatically increment upon phlebotomist verification of blood donations.
  - Strict validation prevents dispensing below zero.
- **90-Day Medical Cooldown**: Visual countdown badges showing when a donor is next eligible to donate whole blood.
- **Interactive Eligibility Quiz**: Public screening assessment helping prospective donors verify medical readiness.
- **Digital Donor ID Card**: Printable visual donor credentials with blood type badges and registration verification.
- **Official Hospital Dispatch Receipts**: Printable requisition slips with dual authorization signatures for custody and transport.
- **CSV Data Export**: One-click administrative reporting for inventory audits, requisitions, and donation logs.

---

## System Architecture & File Structure

```
blood_bank_management_system/
├── app/
│   ├── __init__.py               # Flask application factory, LoginManager, DB init
│   ├── models.py                 # SQLAlchemy relational models (User, Profiles, Inventory, Requests, Camps, BloodBagUnit, EmergencyAlert)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_predictor.py       # AI blood demand forecasting engine
│   │   ├── donor_matcher.py      # Location-based donor matching & alert dispatcher
│   │   └── qr_service.py         # QR code generator & blood unit verifier
│   ├── routes/
│   │   ├── __init__.py           # Role decorators (@admin_required, @donor_required, @hospital_required)
│   │   ├── main.py               # Public homepage, live stock checker, eligibility quiz, camps directory
│   │   ├── auth.py               # Login, registration (donor & hospital), logout
│   │   ├── admin.py              # Operational dashboard, AI predictions, QR tracker, scanner, emergency matcher, CSV export
│   │   ├── donor.py              # Personal dashboard, emergency appeals, donation scheduling, history, digital donor card
│   │   └── hospital.py           # Hospital dashboard, emergency requisition submission, tracking, printable receipts
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css         # Modern medical theme, responsive cards, print media rules
│   │   └── js/
│   │       └── main.js           # Interactive eligibility quiz, alert auto-dismissal, tooltips
│   └── templates/
│       ├── base.html             # Base layout with Life Saver branding, alerts, footer
│       ├── index.html            # Landing page with live stock snapshot & AI feature highlights
│       ├── stock.html            # Public live stock monitor with group filtering
│       ├── eligibility.html      # Interactive 5-question donor eligibility checker
│       ├── camps.html            # Community blood drives directory & search
│       ├── auth/
│       │   ├── login.html        # Secure portal sign-in with quick-fill demo buttons
│       │   ├── register_donor.html
│       │   └── register_hospital.html
│       ├── admin/
│       │   ├── dashboard.html    # Executive dashboard with Chart.js analytics & request queue
│       │   ├── ai_predictions.html # AI demand forecasting dashboard
│       │   ├── emergency_match.html # Location-based emergency donor matcher
│       │   ├── qr_tracker.html   # QR code blood unit inventory audit
│       │   ├── qr_scanner.html   # QR & barcode scanner console
│       │   ├── unit_label.html   # Printable ISBT-128 sterile blood bag label
│       │   ├── inventory.html    # Stock management, threshold alerts, unit adjustments
│       │   ├── requests.html     # Requisition triage (Approve & Deduct / Reject / Match)
│       │   ├── donations.html    # Phlebotomy logging & inventory incrementation
│       │   ├── donors.html       # Registered donors base with search & filters
│       │   ├── hospitals.html    # Partner healthcare institutions directory
│       │   └── camps.html        # Blood camp scheduler & organizer console
│       ├── donor/
│       │   ├── dashboard.html    # Donor dashboard, emergency appeals banner, cooldown progress
│       │   ├── donate.html       # Appointment scheduling & venue selector
│       │   ├── history.html      # Personal donation log
│       │   ├── donor_card.html   # Official printable Digital Blood Donor Pass
│       │   └── profile.html      # Contact and medical disclosures management
│       └── hospital/
│           ├── dashboard.html    # Institutional overview & active requisition status
│           ├── request_blood.html# Emergency blood requisition form with urgency tiers
│           ├── history.html      # Requisition tracking & archives
│           └── receipt.html      # Official printable clinical dispatch voucher
├── config.py                     # Configuration settings (SQLite default / MySQL switch)
├── run.py                        # Application entry point with auto-db-creation & seeder
├── seed_data.py                  # Demo data populator (Admin, Donors, Hospitals, Stock, Camps, BloodBagUnits, Alerts)
├── requirements.txt              # Project dependencies
├── tests/
│   ├── __init__.py
│   └── test_bbms.py              # Automated test suite (12 tests covering AI, Geo-matching, QR tracking, Auth, RBAC)
└── README.md                     # Comprehensive documentation
```

---

## Pre-Seeded Demo Accounts

The database comes pre-populated with realistic demo accounts across all user roles:

| Role | Email Address | Password | Features Accessible |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@bloodbank.org` | `Admin@123` | Full administrative oversight, AI demand forecasting, QR unit tracking, emergency matching, CSV export |
| **Hospital** | `citygeneral@hospital.org` | `Hospital@123` | City General Hospital emergency requisition desk |
| **Hospital** | `stjude@hospital.org` | `Hospital@123` | St. Jude Trauma & Emergency Center |
| **Donor** | `john.doe@email.com` | `Donor@123` | O+ Donor (Eligible to donate, view emergency appeals, Digital Donor Card) |
| **Donor** | `sarah.c@email.com` | `Donor@123` | A+ Donor (Currently in 90-day cooldown) |
| **Donor** | `emily.davis@email.com` | `Donor@123` | O- Universal Red Cell Donor |

> **Note**: The login page at `/auth/login` includes one-click quick autofill buttons to switch between demo roles with a single click.

---

## Installation & Quickstart Guide

### 1. Prerequisites
- Python 3.10 or higher
- pip package manager

### 2. Navigate to Project Directory
```powershell
cd C:\Users\varun\.gemini\antigravity\scratch\blood_bank_management_system
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt qrcode[pil]
```

### 4. Populate Database
By default, the application runs on **SQLite3** (`bloodbank.db`), requiring **zero manual configuration**.

To initialize tables and populate demo data:
```powershell
python seed_data.py
```

#### Optional: Switching to MySQL
To use MySQL instead of SQLite, configure the `DATABASE_URL` environment variable:
```powershell
$env:DATABASE_URL="mysql+pymysql://<user>:<password>@localhost:3306/<database_name>"
pip install pymysql cryptography
python seed_data.py
```

### 5. Launch the Application
```powershell
python run.py
```
Open your web browser and navigate to:
**`http://127.0.0.1:5000`**

---

## Running Automated Tests

A comprehensive 12-test unit test suite is included in `tests/test_bbms.py`:

```powershell
python -m unittest discover -s tests -v
```

Tests cover:
- AI demand prediction calculations across all 8 blood groups and confidence metrics.
- Location-based emergency donor matching, red cell compatibility, and ranking.
- QR code generation, unit enrollment, and shelf life surveillance.
- Simulated emergency SMS & Email alert dispatching.
- Donor authentication and 90-day cooldown logic.
- Inventory consistency and transaction safety guards.
- Administrative CSV exports.

---

## License & Citation
Developed for healthcare professionals, regional blood banks, and medical centers to modernize and safeguard life-saving blood supply chains.
