
import sys
import os
from sqlalchemy import inspect
from app import create_app, db

# Use development config to connect to real DB
app = create_app('development')
with app.app_context():
    print(f"Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    engine = db.engine
    inspector = inspect(engine)
    
    # Check if table exists
    tables = inspector.get_table_names()
    print(f"Tables found: {tables}")
    
    if 'animals' in tables:
        columns = inspector.get_columns('animals')
        print("Columns in 'animals' table:")
        for column in columns:
            print(f"- {column['name']} ({column['type']})")

        # Check for presence of 'idFather' vs 'id_father'
        names = [c['name'] for c in columns]
        if 'idFather' in names:
            print("Found 'idFather'")
        if 'idfather' in names:
            print("Found 'idfather'")
        if 'id_father' in names:
            print("Found 'id_father'")
    else:
        print("Table 'animals' not found in this database.")
