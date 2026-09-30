import os
from app import create_app, db
from app.firebase_db import get_db_mode
from seed_firebase import seed_firebase

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Ensure database is seeded with initial master data
        seed_firebase()

    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')

    mode = get_db_mode()
    print(f"\n=======================================================")
    print(f"  Life Saver - Intelligent Blood Bank Management System")
    print(f"  Firebase Database Mode: [{mode}]")
    print(f"  Access Portal: http://{host}:{port}")
    print(f"=======================================================\n")

    app.run(host=host, port=port, debug=debug)
