
import sys
import os
import logging
from flask import Flask, abort

# Configure dummy logger
logging.basicConfig(level=logging.INFO)

try:
    from app import create_app, db
    app = create_app('testing')
    
    # Define a route that triggers an error
    @app.route('/trigger-500')
    def trigger_error():
        # Raise generic exception to trigger internal_error handler
        raise Exception("Simulated Internal Error")

    @app.route('/trigger-integrity')
    def trigger_integrity():
        from sqlalchemy.exc import IntegrityError
        # Simulate integrity error
        raise IntegrityError("Simulated Integrity Error", params={}, orig="test")

    with app.test_client() as client:
        print("Testing generic 500 error handler...")
        try:
            resp = client.get('/trigger-500')
            print(f"Response status: {resp.status_code}")
            print(f"Response json: {resp.get_json()}")
        except Exception as e:
            print(f"Request failed: {e}")
            import traceback
            traceback.print_exc()

        print("\nTesting integrity error handler...")
        try:
            resp = client.get('/trigger-integrity')
            print(f"Response status: {resp.status_code}")
            print(f"Response json: {resp.get_json()}")
        except Exception as e:
            print(f"Request failed: {e}")
            import traceback
            traceback.print_exc()


except Exception as e:
    print(f"CRITICAL FAILURE: {e}")
    import traceback
    traceback.print_exc()
