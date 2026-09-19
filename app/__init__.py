from datetime import datetime, timezone
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    # Register models & user loader
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.donor import donor_bp
    from app.routes.hospital import hospital_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(donor_bp, url_prefix='/donor')
    app.register_blueprint(hospital_bp, url_prefix='/hospital')

    # Global template context
    @app.context_processor
    def inject_globals():
        current_time = datetime.now(timezone.utc)
        return {
            'now': current_time,
            'current_year': current_time.year,
            'blood_groups': app.config.get('BLOOD_GROUPS', ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'])
        }

    # Custom template filters
    @app.template_filter('format_datetime')
    def format_datetime(value, format='%b %d, %Y %I:%M %p'):
        if value is None:
            return 'N/A'
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except Exception:
                return value
        return value.strftime(format)

    @app.template_filter('format_date')
    def format_date(value, format='%b %d, %Y'):
        if value is None:
            return 'N/A'
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except Exception:
                return value
        return value.strftime(format)

    return app
