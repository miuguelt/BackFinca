
import sys
import os
import logging
from flask import Flask

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    print("Attempting to import app...")
    from app import create_app, db
    print("App imported successfully.")
    
    app = create_app('testing')
    print("App created successfully.")
    
    with app.app_context():
        print("Checking AnimalDiseases model match...")
        from app.models import AnimalDisease
        print(f"AnimalDisease class: {AnimalDisease}")
        
        print("Checking AnimalFields model match...")
        from app.models import AnimalField
        from app.models.animalFields import AnimalFields
        print(f"AnimalField alias: {AnimalField}")
        print(f"AnimalFields class: {AnimalFields}")
        
        print("Checking namespaces...")
        from app.namespaces.animal_diseases_namespace import animal_diseases_ns
        from app.namespaces.animal_fields_namespace import animal_fields_ns
        print("Namespaces imported.")

        # Simulate error handler trigger
        from app.utils.error_handlers import register_error_handlers
        print("Error handlers registered.")

except Exception as e:
    print(f"\nCRITICAL ERROR: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
