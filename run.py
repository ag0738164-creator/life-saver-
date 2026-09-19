import os
from app import create_app, db
from seed_data import seed_database

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Ensure database tables exist and are seeded
        db.create_all()
        seed_database()

    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')

    print(f"\n=======================================================")
    print(f"  Blood Bank Management System (BBMS) is running!")
    print(f"  Local URL: http://{host}:{port}")
    print(f"=======================================================\n")

    app.run(host=host, port=port, debug=debug)
