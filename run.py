import os
from app import create_app
from app.models import db
from seed import seed_database

app = create_app(os.environ.get('FLASK_CONFIG', 'development'))


@app.cli.command('init-db')
def init_db_command():
    """Create all relational database tables."""
    with app.app_context():
        db.create_all()
        print("Database schema tables created successfully.")


@app.cli.command('seed')
def seed_command():
    """Seed the database with sample demo accounts, societies, and events."""
    seed_database()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='127.0.0.1', port=port, debug=True)
