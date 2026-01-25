from app import create_app, db
from sqlalchemy import inspect
import os

def main():
    flask_env = os.getenv('FLASK_ENV') or 'development'
    app = create_app(flask_env)
    with app.app_context():
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Tables found in database: {tables}")
        
        required_tables = [
            'animals', 'diseases', 'treatments', 'genetic_improvements', 
            'control', 'user', 'breeds', 'species'
        ]
        
        missing = [t for t in required_tables if t not in tables]
        if missing:
            print(f"Missing tables: {missing}")
        else:
            print("All required tables are present.")

if __name__ == '__main__':
    main()
