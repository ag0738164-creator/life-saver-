from datetime import datetime, date, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='donor')  # 'admin', 'donor', 'hospital'
    phone = db.Column(db.String(20), nullable=True)
    city = db.Column(db.String(80), nullable=True)
    address = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    donor_profile = db.relationship('DonorProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    hospital_profile = db.relationship('HospitalProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    blood_requests = db.relationship('BloodRequest', backref='hospital', lazy='dynamic', cascade='all, delete-orphan')
    donations = db.relationship('DonationRecord', backref='donor', lazy='dynamic', cascade='all, delete-orphan')
    emergency_alerts = db.relationship('EmergencyAlert', backref='donor', lazy='dynamic', cascade='all, delete-orphan')
    blood_units_donated = db.relationship('BloodBagUnit', foreign_keys='BloodBagUnit.donor_id', backref='donor', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_donor(self):
        return self.role == 'donor'

    @property
    def is_hospital(self):
        return self.role == 'hospital'

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class DonorProfile(db.Model):
    __tablename__ = 'donor_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    blood_group = db.Column(db.String(5), nullable=False)
    gender = db.Column(db.String(10), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    weight = db.Column(db.Float, nullable=True)
    last_donation_date = db.Column(db.Date, nullable=True)
    medical_notes = db.Column(db.Text, nullable=True)

    @property
    def days_since_last_donation(self):
        if not self.last_donation_date:
            return None
        return (date.today() - self.last_donation_date).days

    @property
    def is_eligible(self):
        # Age check
        if self.age and self.age < 18:
            return False
        # Weight check (minimum 50kg standard)
        if self.weight and self.weight < 50:
            return False
        # Cooldown check: 90 days between donations
        if self.last_donation_date:
            return (date.today() - self.last_donation_date).days >= 90
        return True

    @property
    def next_eligible_date(self):
        if not self.last_donation_date:
            return date.today()
        eligible_date = self.last_donation_date + timedelta(days=90)
        return max(date.today(), eligible_date)

    @property
    def cooldown_days_remaining(self):
        if not self.last_donation_date:
            return 0
        diff = 90 - (date.today() - self.last_donation_date).days
        return max(0, diff)

    def __repr__(self):
        return f'<DonorProfile User {self.user_id} - {self.blood_group}>'


class HospitalProfile(db.Model):
    __tablename__ = 'hospital_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    license_number = db.Column(db.String(80), nullable=False)
    hospital_type = db.Column(db.String(50), default='General')  # 'Government', 'Private', 'Specialty', 'Trauma Center'
    emergency_contact = db.Column(db.String(20), nullable=True)
    is_verified = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<HospitalProfile {self.license_number}>'


class BloodInventory(db.Model):
    __tablename__ = 'blood_inventory'

    id = db.Column(db.Integer, primary_key=True)
    blood_group = db.Column(db.String(5), unique=True, nullable=False)
    units_available = db.Column(db.Integer, default=0, nullable=False)
    critical_threshold = db.Column(db.Integer, default=5, nullable=False)
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @property
    def is_critical(self):
        return self.units_available <= self.critical_threshold

    @property
    def status_label(self):
        if self.units_available == 0:
            return 'Depleted'
        elif self.units_available <= self.critical_threshold:
            return 'Critical'
        elif self.units_available <= (self.critical_threshold * 2):
            return 'Low'
        else:
            return 'Sufficient'

    @property
    def status_badge_class(self):
        if self.units_available == 0:
            return 'bg-dark'
        elif self.units_available <= self.critical_threshold:
            return 'bg-danger'
        elif self.units_available <= (self.critical_threshold * 2):
            return 'bg-warning text-dark'
        else:
            return 'bg-success'

    def __repr__(self):
        return f'<BloodInventory {self.blood_group}: {self.units_available} units>'


class BloodRequest(db.Model):
    __tablename__ = 'blood_requests'

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    blood_group = db.Column(db.String(5), nullable=False)
    units_requested = db.Column(db.Integer, nullable=False)
    urgency = db.Column(db.String(20), default='Normal')  # 'Normal', 'Critical', 'Emergency'
    patient_name = db.Column(db.String(100), nullable=False)
    patient_case_no = db.Column(db.String(50), nullable=True)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Pending')  # 'Pending', 'Approved', 'Rejected', 'Dispensed'
    admin_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    processed_at = db.Column(db.DateTime, nullable=True)

    emergency_alerts = db.relationship('EmergencyAlert', backref='request', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def urgency_badge_class(self):
        if self.urgency == 'Emergency':
            return 'bg-danger text-white pulse-animation'
        elif self.urgency == 'Critical':
            return 'bg-warning text-dark'
        return 'bg-info text-dark'

    @property
    def status_badge_class(self):
        if self.status in ('Approved', 'Dispensed'):
            return 'bg-success'
        elif self.status == 'Rejected':
            return 'bg-danger'
        return 'bg-warning text-dark'

    def __repr__(self):
        return f'<BloodRequest #{self.id} {self.blood_group} ({self.units_requested} units) - {self.status}>'


class DonationCamp(db.Model):
    __tablename__ = 'donation_camps'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    organized_by = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(80), nullable=False)
    camp_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(20), default='09:00 AM')
    end_time = db.Column(db.String(20), default='05:00 PM')
    contact_person = db.Column(db.String(100), nullable=True)
    contact_phone = db.Column(db.String(20), nullable=True)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Upcoming')  # 'Upcoming', 'Ongoing', 'Completed', 'Cancelled'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    donations = db.relationship('DonationRecord', backref='camp', lazy='dynamic')

    def __repr__(self):
        return f'<DonationCamp {self.title} on {self.camp_date}>'


class DonationRecord(db.Model):
    __tablename__ = 'donation_records'

    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    camp_id = db.Column(db.Integer, db.ForeignKey('donation_camps.id', ondelete='SET NULL'), nullable=True)
    blood_group = db.Column(db.String(5), nullable=False)
    units_donated = db.Column(db.Integer, default=1, nullable=False)
    donation_date = db.Column(db.Date, default=date.today, nullable=False)
    status = db.Column(db.String(20), default='Completed')  # 'Scheduled', 'Completed', 'Cancelled'
    verified_by = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def status_badge_class(self):
        if self.status == 'Completed':
            return 'bg-success'
        elif self.status == 'Scheduled':
            return 'bg-info text-dark'
        return 'bg-secondary'

    def __repr__(self):
        return f'<DonationRecord #{self.id} Donor {self.donor_id} ({self.blood_group})>'


class BloodBagUnit(db.Model):
    __tablename__ = 'blood_bag_units'

    id = db.Column(db.Integer, primary_key=True)
    unit_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    blood_group = db.Column(db.String(5), nullable=False, index=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    donation_id = db.Column(db.Integer, db.ForeignKey('donation_records.id', ondelete='SET NULL'), nullable=True)
    component_type = db.Column(db.String(50), default='Packed Red Blood Cells')  # 'Whole Human Blood', 'Packed Red Blood Cells', 'Platelets', 'Fresh Frozen Plasma'
    volume_ml = db.Column(db.Integer, default=450)
    collection_date = db.Column(db.Date, default=date.today, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    screening_results = db.Column(db.String(200), default='HIV: Non-Reactive | HBV: Non-Reactive | HCV: Non-Reactive | Syphilis: Non-Reactive')
    storage_location = db.Column(db.String(100), default='Cold Vault Compartment A')
    storage_temp = db.Column(db.String(20), default='2°C - 6°C')
    status = db.Column(db.String(30), default='In Storage')  # 'In Storage', 'Reserved', 'Issued', 'Quarantined', 'Expired', 'Discarded'
    issued_to_hospital_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    issued_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    issued_hospital = db.relationship('User', foreign_keys=[issued_to_hospital_id], backref='issued_blood_units')
    donation = db.relationship('DonationRecord', backref='blood_bag_unit', uselist=False)

    @property
    def is_expired(self):
        return date.today() > self.expiry_date

    @property
    def days_until_expiry(self):
        return (self.expiry_date - date.today()).days

    @property
    def status_badge_class(self):
        if self.status == 'In Storage':
            if self.is_expired:
                return 'bg-danger'
            elif self.days_until_expiry <= 5:
                return 'bg-warning text-dark'
            return 'bg-success'
        elif self.status == 'Issued':
            return 'bg-primary'
        elif self.status == 'Reserved':
            return 'bg-info text-dark'
        elif self.status in ('Quarantined', 'Discarded', 'Expired'):
            return 'bg-danger'
        return 'bg-secondary'

    def get_qr_image(self):
        from app.services.qr_service import BloodUnitQRService
        payload = BloodUnitQRService.build_unit_payload(self)
        return BloodUnitQRService.generate_qr_base64(payload)

    def __repr__(self):
        return f'<BloodBagUnit {self.unit_number} ({self.blood_group}) - {self.status}>'


class EmergencyAlert(db.Model):
    __tablename__ = 'emergency_alerts'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('blood_requests.id', ondelete='CASCADE'), nullable=False)
    donor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    channel = db.Column(db.String(10), default='SMS')  # 'SMS', 'Email'
    recipient_contact = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='Delivered')  # 'Dispatched', 'Delivered', 'Accepted', 'Declined'
    message_content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<EmergencyAlert #{self.id} Donor {self.donor_id} via {self.channel} ({self.status})>'

