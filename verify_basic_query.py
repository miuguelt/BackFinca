
import sys
import traceback
from app import create_app, db
from app.models import Animal, AnimalDisease

app = create_app('development')
with app.app_context():
    print("Testing Animal relationships...")
    try:
        animal = Animal.query.first()
        if animal:
            print(f"Fetched animal: {animal.id}, Record: {animal.record}")
            
            # Test relationships
            print("Accessing lazy loaded relationships...")
            # Father/Mother use 'joined' loading or 'select' depending on config
            if animal.father:
                print(f"Father: {animal.father.record}")
            else:
                print("No father")
                
            if animal.mother:
                print(f"Mother: {animal.mother.record}")
            else:
                print("No mother")
                
            # Access dynamic relationships (lazy='dynamic') requires .all() or iteration
            print("Accessing diseases (dynamic)...")
            diseases_query = animal.diseases
            print(f"Diseases query: {diseases_query}")
            diseases = diseases_query.all()
            print(f"Diseases count: {len(diseases)}")
            
            # Test loading all diseases directly
            print("Querying AnimalDisease directly...")
            all_diseases = AnimalDisease.query.limit(5).all()
            print(f"Total diseases (limit 5): {len(all_diseases)}")

    except Exception:
        print("Query failed during relationship access!")
        traceback.print_exc()

    print("\nTesting Error Handler (simulation)...")
    try:
        from app.utils.error_handlers import register_error_handlers
        # We can't easily trigger the flask error handler without a request, 
        # but we can check if the variables inside are bound correctly if we could inspect closures.
        # Instead, let's just make sure imports inside functions work.
        from app.utils.response_handler import APIResponse
        print("APIResponse import ok.")
        
    except Exception as e:
        print(f"Error handler check failed: {e}")
        traceback.print_exc()
