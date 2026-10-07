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
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID', 'lifesaver-2df25')

    # Web SDK Configuration for lifesaver-2df25
    FIREBASE_CONFIG = {
        'apiKey': os.environ.get('FIREBASE_API_KEY', 'AIzaSyDjJ8NA1ipMnuBBSfU6GJ7kA48kU0m6_5g'),
        'authDomain': os.environ.get('FIREBASE_AUTH_DOMAIN', 'lifesaver-2df25.firebaseapp.com'),
        'projectId': os.environ.get('FIREBASE_PROJECT_ID', 'lifesaver-2df25'),
        'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET', 'lifesaver-2df25.firebasestorage.app'),
        'messagingSenderId': os.environ.get('FIREBASE_MESSAGING_SENDER_ID', '963027586131'),
        'appId': os.environ.get('FIREBASE_APP_ID', '1:963027586131:web:2b129ae969107cca050aa6')
    }
    
    # Local Firestore fallback file for zero-credential offline development
    LOCAL_FIRESTORE_PATH = os.path.join(BASE_DIR, 'firebase_db_data.json')
    
    # Blood bank standard blood groups
    BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    
    # Default minimum safe units threshold per blood group
    DEFAULT_CRITICAL_THRESHOLD = 5
    
    # Minimum waiting period between whole blood donations (in days)
    DONATION_COOLDOWN_DAYS = 90
