import json
from app import create_app
from app.models.animals import Animals

def verify_generic_endpoints():
    app = create_app()
    with app.app_context():
        # Note: We can't easily test HTTP endpoints with the full stack here without a running server,
        # but we can simulate the resource calls.
        
        from app.utils.namespace_helpers import create_optimized_namespace
        from flask import Flask, request
        
        # We'll check if the resources are correctly registered in the namespace
        from app.namespaces.animals_namespace import animals_ns
        
        print("Checking Animals Namespace resources...")
        # Search for the added resources
        found_deps = False
        found_batch = False
        
        for resource, urls, kwargs in animals_ns.resources:
            url_pattern = urls[0]
            if '/<int:record_id>/dependencies' in url_pattern:
                found_deps = True
                print(f"Found dependencies endpoint: {url_pattern}")
            if '/batch-dependencies' in url_pattern:
                found_batch = True
                print(f"Found batch-dependencies endpoint: {url_pattern}")
        
        if found_deps and found_batch:
            print("SUCCESS: Generic endpoints are correctly registered in the namespace!")
        else:
            print(f"FAILURE: Missing endpoints. Deps: {found_deps}, Batch: {found_batch}")

        # Test the mapping in Animals
        print("\nChecking Animals mapping...")
        mapping = getattr(Animals, '_field_mapping', {})
        if mapping.get('idFather') == 'father_id':
            print("SUCCESS: Animals field mapping is correct!")
        else:
            print(f"FAILURE: Animals field mapping is missing or incorrect: {mapping}")

if __name__ == "__main__":
    verify_generic_endpoints()
