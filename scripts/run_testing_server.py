"""Run the Flask app in testing mode (SQLite in-memory) for local docs verification.

Usage: Run this script and open http://127.0.0.1:8081/api/v1/docs/
"""
import sys
import os

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app, db

app = create_app('testing')

if __name__ == '__main__':
    with app.app_context():
        # Create tables in the in-memory database for the running process
        db.create_all()
    # Run without SSL for local testing
    app.run(host='127.0.0.1', port=8081, debug=True)
