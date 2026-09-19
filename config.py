import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'bbms-super-secret-key-2026-prod-dev')
    
    # Default SQLite, or use MySQL/PostgreSQL via DATABASE_URL environment variable
    # Example MySQL URI: mysql+pymysql://username:password@localhost/bloodbank_db
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'bloodbank.db')}"
    )
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Blood bank standard blood groups
    BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    
    # Default minimum safe units threshold per blood group
    DEFAULT_CRITICAL_THRESHOLD = 5
    
    # Minimum waiting period between whole blood donations (in days)
    DONATION_COOLDOWN_DAYS = 90
