
import sys
import os
import logging
from flask import Flask

# Configure dummy logger
logging.basicConfig(level=logging.INFO)

try:
    from app import create_app, db
    
    # We will test if we can hit an endpoint that uses AnimalDisease
    # to ensure the namespace and model are loaded correctly.
    app = create_app('testing')
    
    with app.test_client() as client:
        # Assuming we have a way to list diseases. 
        # The logs showed successful response from /api/v1/animal-diseases
        # But we don't have authentication setup easily in this script unless we mock it.
        # However, checking if the MODULE loads and imports is a good first step.
        print("Importing animal_diseases_namespace...")
        from app.namespaces.animal_diseases_namespace import animal_diseases_ns
        print("Success.")

        # Check AnimalFields too
        print("Importing animal_fields_namespace...")
        from app.namespaces.animal_fields_namespace import animal_fields_ns
        print("Success.")
        
        # Test basic Animals query inside app context
        with app.app_context():
            from app.models import Animal
            c = Animal.query.count()
            print(f"Animals count in test DB: {c}")

except Exception as e:
    print(f"CRITICAL FAILURE: {e}")
    import traceback
    traceback.print_exc()
