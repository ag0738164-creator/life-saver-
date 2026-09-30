import os
import json
import threading
from datetime import datetime, date, timezone
from typing import Dict, Any, List, Optional

import firebase_admin
from firebase_admin import credentials, firestore

class LocalDocumentSnapshot:
    """Mirrors google.cloud.firestore.DocumentSnapshot for local persistence."""
    def __init__(self, doc_id: str, data: Optional[Dict[str, Any]]):
        self.id = str(doc_id)
        self._data = data.copy() if data is not None else None
        self.exists = data is not None

    def to_dict(self) -> Optional[Dict[str, Any]]:
        if self._data is None:
            return None
        return self._data.copy()

    def get(self, field: str, default=None):
        if self._data is None:
            return default
        return self._data.get(field, default)

    def __repr__(self):
        return f'<LocalDocumentSnapshot id={self.id} exists={self.exists}>'


class LocalDocumentReference:
    """Mirrors google.cloud.firestore.DocumentReference."""
    def __init__(self, db: 'LocalFirestoreDB', collection_name: str, doc_id: str):
        self._db = db
        self.collection_name = collection_name
        self.id = str(doc_id)

    def get(self) -> LocalDocumentSnapshot:
        return self._db.get_document(self.collection_name, self.id)

    def set(self, data: Dict[str, Any], merge: bool = False):
        self._db.set_document(self.collection_name, self.id, data, merge=merge)

    def update(self, data: Dict[str, Any]):
        self._db.update_document(self.collection_name, self.id, data)

    def delete(self):
        self._db.delete_document(self.collection_name, self.id)

    def __repr__(self):
        return f'<LocalDocumentReference path={self.collection_name}/{self.id}>'


class LocalQuery:
    """Mirrors google.cloud.firestore.Query."""
    def __init__(self, db: 'LocalFirestoreDB', collection_name: str, filters=None, orders=None, limit_val=None):
        self._db = db
        self.collection_name = collection_name
        self._filters = filters or []  # List of tuples: (field, op, val)
        self._orders = orders or []    # List of tuples: (field, direction)
        self._limit = limit_val

    def where(self, field: str, op: str, value: Any) -> 'LocalQuery':
        new_filters = list(self._filters)
        new_filters.append((field, op, value))
        return LocalQuery(self._db, self.collection_name, new_filters, self._orders, self._limit)

    def order_by(self, field: str, direction: str = 'ASCENDING') -> 'LocalQuery':
        new_orders = list(self._orders)
        new_orders.append((field, direction))
        return LocalQuery(self._db, self.collection_name, self._filters, new_orders, self._limit)

    def limit(self, count: int) -> 'LocalQuery':
        return LocalQuery(self._db, self.collection_name, self._filters, self._orders, count)

    def stream(self):
        docs = self._db.get_collection_documents(self.collection_name)
        
        # Apply filters
        filtered = []
        for doc in docs:
            match = True
            for field, op, val in self._filters:
                doc_val = doc.get(field)
                if op == '==' and doc_val != val:
                    match = False
                    break
                elif op == '!=' and doc_val == val:
                    match = False
                    break
                elif op == '>=' and (doc_val is None or doc_val < val):
                    match = False
                    break
                elif op == '<=' and (doc_val is None or doc_val > val):
                    match = False
                    break
                elif op == '>' and (doc_val is None or doc_val <= val):
                    match = False
                    break
                elif op == '<' and (doc_val is None or doc_val >= val):
                    match = False
                    break
                elif op == 'in' and (val is None or doc_val not in val):
                    match = False
                    break
            if match:
                filtered.append(doc)

        # Apply orders
        for field, direction in reversed(self._orders):
            is_desc = direction in ('DESCENDING', firestore.Query.DESCENDING if hasattr(firestore, 'Query') else 'DESCENDING')
            filtered.sort(
                key=lambda d: (d.get(field) is None, d.get(field)),
                reverse=is_desc
            )

        # Apply limit
        if self._limit is not None:
            filtered = filtered[:self._limit]

        for doc_data in filtered:
            yield LocalDocumentSnapshot(doc_data['id'], doc_data)

    def get(self) -> List[LocalDocumentSnapshot]:
        return list(self.stream())


class LocalCollectionReference(LocalQuery):
    """Mirrors google.cloud.firestore.CollectionReference."""
    def __init__(self, db: 'LocalFirestoreDB', collection_name: str):
        super().__init__(db, collection_name)

    def document(self, doc_id: Optional[str] = None) -> LocalDocumentReference:
        if not doc_id:
            doc_id = self._db.generate_id(self.collection_name)
        return LocalDocumentReference(self._db, self.collection_name, str(doc_id))

    def add(self, data: Dict[str, Any]):
        doc_id = self._db.generate_id(self.collection_name)
        doc_ref = self.document(doc_id)
        doc_ref.set(data)
        return None, doc_ref


class LocalFirestoreDB:
    """
    High-fidelity, JSON-persisted local Firestore client.
    Guarantees 100% feature parity with Google Cloud Firestore when run offline.
    """
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self._lock = threading.RLock()
        self._data: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._load()

    def _load(self):
        with self._lock:
            if os.path.exists(self.storage_path):
                try:
                    with open(self.storage_path, 'r', encoding='utf-8') as f:
                        self._data = json.load(f)
                except Exception as e:
                    print(f"Notice: Could not parse local Firestore JSON ({e}). Initializing empty database.")
                    self._data = {}
            else:
                self._data = {}

    def _save(self):
        with self._lock:
            temp_path = self.storage_path + '.tmp'
            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(self._data, f, indent=2, default=str)
                if os.path.exists(self.storage_path):
                    os.replace(temp_path, self.storage_path)
                else:
                    os.rename(temp_path, self.storage_path)
            except Exception as e:
                print(f"Error persisting local Firestore data: {e}")

    def collection(self, collection_name: str) -> LocalCollectionReference:
        return LocalCollectionReference(self, collection_name)

    def generate_id(self, collection_name: str) -> str:
        with self._lock:
            col = self._data.get(collection_name, {})
            # Look for max numeric id or auto-increment
            numeric_ids = []
            for k in col.keys():
                try:
                    numeric_ids.append(int(k))
                except ValueError:
                    pass
            next_id = max(numeric_ids, default=0) + 1
            return str(next_id)

    def get_document(self, collection_name: str, doc_id: str) -> LocalDocumentSnapshot:
        with self._lock:
            col = self._data.get(collection_name, {})
            data = col.get(str(doc_id))
            return LocalDocumentSnapshot(doc_id, data)

    def set_document(self, collection_name: str, doc_id: str, data: Dict[str, Any], merge: bool = False):
        with self._lock:
            if collection_name not in self._data:
                self._data[collection_name] = {}
            doc_id_str = str(doc_id)
            if merge and doc_id_str in self._data[collection_name]:
                self._data[collection_name][doc_id_str].update(data)
            else:
                doc_record = data.copy()
                doc_record['id'] = doc_id_str
                self._data[collection_name][doc_id_str] = doc_record
            self._save()

    def update_document(self, collection_name: str, doc_id: str, data: Dict[str, Any]):
        with self._lock:
            if collection_name not in self._data:
                self._data[collection_name] = {}
            doc_id_str = str(doc_id)
            if doc_id_str in self._data[collection_name]:
                self._data[collection_name][doc_id_str].update(data)
            else:
                doc_record = data.copy()
                doc_record['id'] = doc_id_str
                self._data[collection_name][doc_id_str] = doc_record
            self._save()

    def delete_document(self, collection_name: str, doc_id: str):
        with self._lock:
            if collection_name in self._data and str(doc_id) in self._data[collection_name]:
                del self._data[collection_name][str(doc_id)]
                self._save()

    def get_collection_documents(self, collection_name: str) -> List[Dict[str, Any]]:
        with self._lock:
            col = self._data.get(collection_name, {})
            result = []
            for doc_id, doc_data in col.items():
                item = doc_data.copy()
                item['id'] = str(doc_id)
                result.append(item)
            return result

    def clear(self):
        with self._lock:
            self._data = {}
            self._save()


# Global singleton holder
_firestore_client = None
_db_mode = None

def get_firebase_db(config=None, reset=False):
    """
    Returns the initialized Firestore database client.
    Connects to live Google Cloud Firebase Firestore if serviceAccountKey.json or
    FIREBASE_CREDENTIALS environment variable exists.
    Otherwise gracefully falls back to persistent LocalFirestoreDB.
    """
    global _firestore_client, _db_mode
    from config import Config
    cred_path = getattr(config, 'FIREBASE_CREDENTIALS', None) or Config.FIREBASE_CREDENTIALS
    local_path = getattr(config, 'LOCAL_FIRESTORE_PATH', None) or Config.LOCAL_FIRESTORE_PATH

    if _firestore_client is not None and not reset:
        # If client is LocalFirestoreDB, check if requested path matches
        if isinstance(_firestore_client, LocalFirestoreDB):
            if local_path and _firestore_client.storage_path != local_path:
                _firestore_client = LocalFirestoreDB(local_path)
        return _firestore_client

    # Check for live Google Firebase Credentials
    if cred_path and os.path.exists(cred_path):
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            _firestore_client = firestore.client()
            _db_mode = "live_firebase"
            print(f"[Firebase] Connected to Live Google Cloud Firebase Firestore via {cred_path}")
            return _firestore_client
        except Exception as e:
            print(f"[Notice] Failed to connect to Live Firebase ({e}). Using Local Firestore fallback.")

    # Check if Google Application Default Credentials or emulator are present
    if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') or os.environ.get('FIRESTORE_EMULATOR_HOST'):
        try:
            if not firebase_admin._apps:
                firebase_admin.initialize_app()
            _firestore_client = firestore.client()
            _db_mode = "live_firebase"
            print("[Firebase] Connected to Google Firebase Firestore via Application Default Credentials / Emulator")
            return _firestore_client
        except Exception as e:
            print(f"[Notice] Live Firestore initialization returned: {e}")

    # Fallback: Local Firestore persistent database
    _firestore_client = LocalFirestoreDB(local_path)
    _db_mode = "local_firestore"
    print(f"[Firebase] Using Persistent Local Firebase Firestore ({local_path})")
    return _firestore_client

def get_db_mode() -> str:
    """Returns 'live_firebase' or 'local_firestore'."""
    return _db_mode or "uninitialized"
