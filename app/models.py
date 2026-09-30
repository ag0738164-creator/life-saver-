import os
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict, Any, Union
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask import abort

from app.firebase_db import get_firebase_db

def _parse_date(val):
    if val is None or isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val).date()
        except Exception:
            try:
                return datetime.strptime(val[:10], '%Y-%m-%d').date()
            except Exception:
                return None
    return None

def _parse_datetime(val):
    if val is None or isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day, tzinfo=timezone.utc)
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except Exception:
            try:
                return datetime.strptime(val, '%Y-%m-%d %H:%M:%S')
            except Exception:
                return None
    return None

def _serialize_val(val):
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    return val


class ModelQuery:
    """
    Unified query interface for Firebase Firestore collections.
    Provides complete compatibility with SQLAlchemy query semantics.
    """
    def __init__(self, model_cls, filters=None, orders=None, limit_count=None):
        self.model_cls = model_cls
        self._filters = filters or []  # List of callables: (item) -> bool
        self._orders = orders or []    # List of (attr_name, is_desc)
        self._limit = limit_count

    def filter_by(self, **kwargs):
        new_filters = list(self._filters)
        for key, val in kwargs.items():
            # Support field equality
            def make_filter(k, v):
                return lambda item: getattr(item, k, None) == v or str(getattr(item, k, None)) == str(v)
            new_filters.append(make_filter(key, val))
        return ModelQuery(self.model_cls, new_filters, self._orders, self._limit)

    def filter(self, *expressions):
        # Support lambda or callable or boolean expression functions
        new_filters = list(self._filters)
        for expr in expressions:
            if callable(expr):
                new_filters.append(expr)
            elif hasattr(expr, '__call__'):
                new_filters.append(expr)
        return ModelQuery(self.model_cls, new_filters, self._orders, self._limit)

    def order_by(self, *orders):
        new_orders = list(self._orders)
        for ord_expr in orders:
            if callable(ord_expr):
                new_orders.append((ord_expr, True))
            elif isinstance(ord_expr, tuple):
                new_orders.append(ord_expr)
            elif isinstance(ord_expr, str):
                if ord_expr.startswith('-'):
                    new_orders.append((ord_expr[1:], True))
                else:
                    new_orders.append((ord_expr, False))
            elif hasattr(ord_expr, 'key'):
                new_orders.append((ord_expr.key, False))
            elif hasattr(ord_expr, 'desc') and callable(getattr(ord_expr, 'desc')):
                attr = getattr(ord_expr, 'element', ord_expr)
                attr_name = getattr(attr, 'name', getattr(attr, 'key', str(ord_expr)))
                new_orders.append((attr_name, True))
            elif hasattr(ord_expr, 'asc') and callable(getattr(ord_expr, 'asc')):
                attr = getattr(ord_expr, 'element', ord_expr)
                attr_name = getattr(attr, 'name', getattr(attr, 'key', str(ord_expr)))
                new_orders.append((attr_name, False))
            elif hasattr(ord_expr, 'name'):
                new_orders.append((ord_expr.name, False))
        return ModelQuery(self.model_cls, self._filters, new_orders, self._limit)

    def limit(self, count: int):
        return ModelQuery(self.model_cls, self._filters, self._orders, count)

    def _execute(self):
        db = get_firebase_db()
        col_ref = db.collection(self.model_cls.collection_name)
        # Fetch documents
        docs = col_ref.get() if hasattr(col_ref, 'get') else col_ref.stream()
        results = []
        for doc in docs:
            data = doc.to_dict() if hasattr(doc, 'to_dict') else doc
            if not data:
                continue
            instance = self.model_cls.from_dict(data, doc.id)
            results.append(instance)

        # Apply in-memory filters
        for f in self._filters:
            results = [item for item in results if f(item)]

        # Apply orders
        for order_spec in reversed(self._orders):
            if isinstance(order_spec, tuple) and len(order_spec) == 2:
                key_or_attr, is_desc = order_spec
                if callable(key_or_attr):
                    results.sort(key=key_or_attr, reverse=is_desc)
                else:
                    attr = str(key_or_attr)
                    results.sort(
                        key=lambda item: (getattr(item, attr, None) is None, getattr(item, attr, None)),
                        reverse=is_desc
                    )

        # Apply limit
        if self._limit is not None:
            results = results[:self._limit]

        return results

    def all(self):
        return self._execute()

    def first(self):
        res = self._execute()
        return res[0] if res else None

    def first_or_404(self):
        res = self.first()
        if not res:
            abort(404)
        return res

    def get(self, doc_id):
        if doc_id is None:
            return None
        res = self.model_cls.get(str(doc_id))
        if res is not None:
            return res
        for item in self._execute():
            if str(item.id) == str(doc_id):
                return item
        return None

    def get_or_404(self, doc_id):
        res = self.get(doc_id)
        if not res:
            abort(404)
        return res

    def count(self):
        return len(self._execute())

    def __iter__(self):
        return iter(self._execute())

    def __len__(self):
        return self.count()

    def __getitem__(self, item):
        res = self._execute()
        return res[item]


class ColumnDescriptor:
    """Allows syntax like Model.created_at.desc() in order_by queries and date filters."""
    def __init__(self, name):
        self.name = name
        self.key = name

    def desc(self):
        return (self.name, True)

    def asc(self):
        return (self.name, False)

    def _safe_val(self, item):
        val = getattr(item, self.name, None)
        if isinstance(val, str):
            parsed = _parse_datetime(val) or _parse_date(val)
            if parsed is not None:
                val = parsed
        return val

    def _normalize_other(self, other, target_val):
        if isinstance(other, datetime) and isinstance(target_val, date) and not isinstance(target_val, datetime):
            return other.date()
        if isinstance(other, datetime) and isinstance(target_val, datetime):
            if target_val.tzinfo is None and other.tzinfo is not None:
                return other.replace(tzinfo=None)
            elif target_val.tzinfo is not None and other.tzinfo is None:
                return other.replace(tzinfo=timezone.utc)
        return other

    def __ge__(self, other):
        def _check(item):
            val = self._safe_val(item)
            if val is None:
                return False
            norm_other = self._normalize_other(other, val)
            return val >= norm_other
        return _check

    def __le__(self, other):
        def _check(item):
            val = self._safe_val(item)
            if val is None:
                return False
            norm_other = self._normalize_other(other, val)
            return val <= norm_other
        return _check

    def __gt__(self, other):
        def _check(item):
            val = self._safe_val(item)
            if val is None:
                return False
            norm_other = self._normalize_other(other, val)
            return val > norm_other
        return _check

    def __lt__(self, other):
        def _check(item):
            val = self._safe_val(item)
            if val is None:
                return False
            norm_other = self._normalize_other(other, val)
            return val < norm_other
        return _check

    def __eq__(self, other):
        return lambda item: getattr(item, self.name, None) == other or str(getattr(item, self.name, '')) == str(other)

    def ilike(self, pattern):
        name = self.name
        clean_pat = pattern.replace('%', '').strip().lower()
        return lambda item: clean_pat in str(getattr(item, self.name, '')).lower()


class MetaFirebaseModel(type):
    """Metaclass to expose Model.query and column descriptors."""
    @property
    def query(cls):
        return ModelQuery(cls)

    def __getattr__(cls, item):
        if not item.startswith('_') and item not in ('collection_name', 'get', 'all', 'create'):
            return ColumnDescriptor(item)
        raise AttributeError(f"{cls.__name__} has no attribute {item}")


class FirebaseBaseModel(metaclass=MetaFirebaseModel):
    collection_name = 'base'

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if k == 'is_active':
                self._is_active = bool(v)
            else:
                try:
                    setattr(self, k, v)
                except AttributeError:
                    pass
        if not hasattr(self, 'id'):
            self.id = kwargs.get('id', None)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], doc_id: str):
        instance = cls(**data)
        instance.id = doc_id
        return instance

    def to_dict(self) -> Dict[str, Any]:
        data = {}
        for k, v in self.__dict__.items():
            if k.startswith('_'):
                continue
            data[k] = _serialize_val(v)
        if hasattr(self, '_is_active'):
            data['is_active'] = self._is_active
        return data

    @classmethod
    def get(cls, doc_id):
        if doc_id is None:
            return None
        db = get_firebase_db()
        doc_ref = db.collection(cls.collection_name).document(str(doc_id))
        snap = doc_ref.get()
        if not snap.exists:
            return None
        return cls.from_dict(snap.to_dict(), snap.id)

    @classmethod
    def all(cls):
        return cls.query.all()

    def save(self):
        db = get_firebase_db()
        col = db.collection(self.collection_name)
        data = self.to_dict()
        if not getattr(self, 'id', None):
            doc_id = db.generate_id(self.collection_name) if hasattr(db, 'generate_id') else col.document().id
            self.id = str(doc_id)
            data['id'] = self.id
        doc_ref = col.document(str(self.id))
        doc_ref.set(data)
        return self

    def delete(self):
        if getattr(self, 'id', None):
            db = get_firebase_db()
            db.collection(self.collection_name).document(str(self.id)).delete()


# ==========================================================
# Domain Models
# ==========================================================

class User(UserMixin, FirebaseBaseModel):
    collection_name = 'users'

    def __init__(self, **kwargs):
        self._is_active = kwargs.get('is_active', True)
        super().__init__(**kwargs)
        self.email = kwargs.get('email', '')
        self.password_hash = kwargs.get('password_hash', '')
        self.name = kwargs.get('name', '')
        self.role = kwargs.get('role', 'donor')
        self.phone = kwargs.get('phone', '')
        self.city = kwargs.get('city', '')
        self.address = kwargs.get('address', '')
        self.created_at = _parse_datetime(kwargs.get('created_at')) or datetime.now(timezone.utc)

    @property
    def is_active(self):
        return getattr(self, '_is_active', True)

    @is_active.setter
    def is_active(self, val):
        self._is_active = bool(val)

    def get_id(self):
        return str(self.id)

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

    @property
    def donor_profile(self):
        return DonorProfile.query.filter_by(user_id=self.id).first()

    @property
    def hospital_profile(self):
        return HospitalProfile.query.filter_by(user_id=self.id).first()

    @property
    def blood_requests(self):
        return BloodRequest.query.filter_by(hospital_id=self.id)

    @property
    def donations(self):
        return DonationRecord.query.filter_by(donor_id=self.id)

    @property
    def emergency_alerts(self):
        return EmergencyAlert.query.filter_by(donor_id=self.id)

    @property
    def blood_units_donated(self):
        return BloodBagUnit.query.filter_by(donor_id=self.id)

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class DonorProfile(FirebaseBaseModel):
    collection_name = 'donor_profiles'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_id = str(kwargs.get('user_id', ''))
        self.blood_group = kwargs.get('blood_group', '')
        self.gender = kwargs.get('gender', '')
        self.age = int(kwargs['age']) if kwargs.get('age') is not None and str(kwargs['age']).isdigit() else None
        self.weight = float(kwargs['weight']) if kwargs.get('weight') is not None else None
        self.last_donation_date = _parse_date(kwargs.get('last_donation_date'))
        self.medical_notes = kwargs.get('medical_notes', '')

    @property
    def user(self):
        return User.get(self.user_id)

    @property
    def days_since_last_donation(self):
        if not self.last_donation_date:
            return None
        return (date.today() - self.last_donation_date).days

    @property
    def is_eligible(self):
        if self.age and self.age < 18:
            return False
        if self.weight and self.weight < 50:
            return False
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


class HospitalProfile(FirebaseBaseModel):
    collection_name = 'hospital_profiles'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_id = str(kwargs.get('user_id', ''))
        self.license_number = kwargs.get('license_number', '')
        self.hospital_type = kwargs.get('hospital_type', 'General Hospital')
        self.emergency_contact = kwargs.get('emergency_contact', '')
        self.is_verified = kwargs.get('is_verified', True)

    @property
    def user(self):
        return User.get(self.user_id)

    def __repr__(self):
        return f'<HospitalProfile {self.license_number}>'


class BloodInventory(FirebaseBaseModel):
    collection_name = 'blood_inventory'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.blood_group = kwargs.get('blood_group', '')
        self.units_available = int(kwargs.get('units_available', 0))
        self.critical_threshold = int(kwargs.get('critical_threshold', 5))
        self.last_updated = _parse_datetime(kwargs.get('last_updated')) or datetime.now(timezone.utc)

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


class BloodRequest(FirebaseBaseModel):
    collection_name = 'blood_requests'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hospital_id = str(kwargs.get('hospital_id', ''))
        self.blood_group = kwargs.get('blood_group', '')
        self.units_requested = int(kwargs.get('units_requested', 1))
        self.urgency = kwargs.get('urgency', 'Normal')
        self.patient_name = kwargs.get('patient_name', '')
        self.patient_case_no = kwargs.get('patient_case_no', '')
        self.reason = kwargs.get('reason', '')
        self.status = kwargs.get('status', 'Pending')
        self.admin_notes = kwargs.get('admin_notes', '')
        self.created_at = _parse_datetime(kwargs.get('created_at')) or datetime.now(timezone.utc)
        self.processed_at = _parse_datetime(kwargs.get('processed_at'))

    @property
    def hospital(self):
        return User.get(self.hospital_id)

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

    @property
    def emergency_alerts(self):
        return EmergencyAlert.query.filter_by(request_id=self.id)

    def __repr__(self):
        return f'<BloodRequest #{self.id} {self.blood_group} ({self.units_requested} units) - {self.status}>'


class DonationCamp(FirebaseBaseModel):
    collection_name = 'donation_camps'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = kwargs.get('title', '')
        self.organized_by = kwargs.get('organized_by', '')
        self.location = kwargs.get('location', '')
        self.city = kwargs.get('city', '')
        self.camp_date = _parse_date(kwargs.get('camp_date')) or date.today()
        self.start_time = kwargs.get('start_time', '09:00 AM')
        self.end_time = kwargs.get('end_time', '05:00 PM')
        self.contact_person = kwargs.get('contact_person', '')
        self.contact_phone = kwargs.get('contact_phone', '')
        self.description = kwargs.get('description', '')
        self.status = kwargs.get('status', 'Upcoming')
        self.created_at = _parse_datetime(kwargs.get('created_at')) or datetime.now(timezone.utc)

    @property
    def donations(self):
        return DonationRecord.query.filter_by(camp_id=self.id)

    def __repr__(self):
        return f'<DonationCamp {self.title} on {self.camp_date}>'


class DonationRecord(FirebaseBaseModel):
    collection_name = 'donation_records'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.donor_id = str(kwargs.get('donor_id', ''))
        self.camp_id = str(kwargs.get('camp_id', '')) if kwargs.get('camp_id') else None
        self.blood_group = kwargs.get('blood_group', '')
        self.units_donated = int(kwargs.get('units_donated', 1))
        self.donation_date = _parse_date(kwargs.get('donation_date')) or date.today()
        self.status = kwargs.get('status', 'Completed')
        self.verified_by = kwargs.get('verified_by', '')
        self.notes = kwargs.get('notes', '')
        self.created_at = _parse_datetime(kwargs.get('created_at')) or datetime.now(timezone.utc)

    @property
    def donor(self):
        return User.get(self.donor_id)

    @property
    def camp(self):
        return DonationCamp.get(self.camp_id) if self.camp_id else None

    @property
    def status_badge_class(self):
        if self.status == 'Completed':
            return 'bg-success'
        elif self.status == 'Scheduled':
            return 'bg-info text-dark'
        return 'bg-secondary'

    @property
    def blood_bag_unit(self):
        return BloodBagUnit.query.filter_by(donation_id=self.id).first()

    def __repr__(self):
        return f'<DonationRecord #{self.id} Donor {self.donor_id} ({self.blood_group})>'


class BloodBagUnit(FirebaseBaseModel):
    collection_name = 'blood_bag_units'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.unit_number = kwargs.get('unit_number', '')
        self.blood_group = kwargs.get('blood_group', '')
        self.donor_id = str(kwargs.get('donor_id', '')) if kwargs.get('donor_id') else None
        self.donation_id = str(kwargs.get('donation_id', '')) if kwargs.get('donation_id') else None
        self.component_type = kwargs.get('component_type', 'Packed Red Blood Cells')
        self.volume_ml = int(kwargs.get('volume_ml', 450))
        self.collection_date = _parse_date(kwargs.get('collection_date')) or date.today()
        self.expiry_date = _parse_date(kwargs.get('expiry_date')) or (date.today() + timedelta(days=35))
        self.screening_results = kwargs.get(
            'screening_results',
            'HIV: Non-Reactive | HBV: Non-Reactive | HCV: Non-Reactive | Syphilis: Non-Reactive'
        )
        self.storage_location = kwargs.get('storage_location', 'Cold Vault Compartment A')
        self.storage_temp = kwargs.get('storage_temp', '2°C - 6°C')
        self.status = kwargs.get('status', 'In Storage')
        self.issued_to_hospital_id = str(kwargs.get('issued_to_hospital_id', '')) if kwargs.get('issued_to_hospital_id') else None
        self.issued_at = _parse_datetime(kwargs.get('issued_at'))
        self.created_at = _parse_datetime(kwargs.get('created_at')) or datetime.now(timezone.utc)

    @property
    def donor(self):
        return User.get(self.donor_id) if self.donor_id else None

    @property
    def issued_hospital(self):
        return User.get(self.issued_to_hospital_id) if self.issued_to_hospital_id else None

    @property
    def donation(self):
        return DonationRecord.get(self.donation_id) if self.donation_id else None

    @property
    def is_expired(self):
        if not self.expiry_date:
            return False
        return date.today() > self.expiry_date

    @property
    def days_until_expiry(self):
        if not self.expiry_date:
            return 0
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


class EmergencyAlert(FirebaseBaseModel):
    collection_name = 'emergency_alerts'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.request_id = str(kwargs.get('request_id', ''))
        self.donor_id = str(kwargs.get('donor_id', ''))
        self.channel = kwargs.get('channel', 'SMS')
        self.recipient_contact = kwargs.get('recipient_contact', '')
        self.status = kwargs.get('status', 'Delivered')
        self.message_content = kwargs.get('message_content', '')
        self.sent_at = _parse_datetime(kwargs.get('sent_at')) or datetime.now(timezone.utc)

    @property
    def request(self):
        return BloodRequest.get(self.request_id)

    @property
    def donor(self):
        return User.get(self.donor_id)

    def __repr__(self):
        return f'<EmergencyAlert #{self.id} Donor {self.donor_id} via {self.channel} ({self.status})>'


# ==========================================================
# Compatibility Session Layer (db.session.add, commit, rollback)
# ==========================================================

class FirebaseSession:
    def __init__(self):
        self._staged: List[FirebaseBaseModel] = []

    def get(self, model_cls, doc_id):
        if hasattr(model_cls, 'get'):
            return model_cls.get(doc_id)
        return None

    def add(self, instance: FirebaseBaseModel):
        if hasattr(instance, 'save'):
            instance.save()
            self._staged.append(instance)

    def add_all(self, instances: List[FirebaseBaseModel]):
        for instance in instances:
            self.add(instance)

    def flush(self):
        for item in self._staged:
            if hasattr(item, 'save'):
                item.save()

    def commit(self):
        for item in self._staged:
            if hasattr(item, 'save'):
                item.save()
        self._staged.clear()

    def rollback(self):
        self._staged.clear()

    def remove(self):
        self._staged.clear()

    def delete(self, instance: FirebaseBaseModel):
        if hasattr(instance, 'delete'):
            instance.delete()


class FirebaseDBAdapter:
    """Provides db.session, db.create_all(), and db.drop_all() compatibility."""
    def __init__(self):
        self.session = FirebaseSession()

    def init_app(self, app):
        pass

    def create_all(self):
        pass

    def drop_all(self):
        db = get_firebase_db()
        if hasattr(db, 'clear'):
            db.clear()


db = FirebaseDBAdapter()
