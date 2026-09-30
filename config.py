import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Life Saver Application Configuration with Firebase Database Support."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'lifesaver-super-secret-firebase-key-2026')
    
    # Firebase configuration
    FIREBASE_CREDENTIALS = os.environ.get(
        'FIREBASE_CREDENTIALS',
        os.path.join(BASE_DIR, 'serviceAccountKey.json')
    )
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID', None)
    
    # Local Firestore fallback file for zero-credential offline development
    LOCAL_FIRESTORE_PATH = os.path.join(BASE_DIR, 'firebase_db_data.json')
    
    # Blood bank standard blood groups
    BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    
    # Default minimum safe units threshold per blood group
    DEFAULT_CRITICAL_THRESHOLD = 5
    
    # Minimum waiting period between whole blood donations (in days)
    DONATION_COOLDOWN_DAYS = 90
