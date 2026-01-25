
import sys
import os
from app import create_app, db
from app.models import AnimalDisease, AnimalField, AnimalImage, Animal

app = create_app('testing')
with app.app_context():
    print(f"Animal count: {Animal.query.count()}")
    print(f"AnimalDisease count: {AnimalDisease.query.count()}")
    print(f"AnimalField count: {AnimalField.query.count()}")
    print(f"AnimalImage count: {AnimalImage.query.count()}")
    
    # Check for a sample animal
    animal = Animal.query.first()
    if animal:
        print(f"Sample Animal ID: {animal.id}")
        print(f"Diseases for this animal: {AnimalDisease.query.filter_by(animal_id=animal.id).count()}")
        print(f"Fields for this animal: {AnimalField.query.filter_by(animal_id=animal.id).count()}")
        print(f"Images for this animal: {AnimalImage.query.filter_by(animal_id=animal.id).count()}")
        
        # Check if we can serialize them using the namespace logic (roughly)
        try:
            diseases = AnimalDisease.query.filter_by(animal_id=animal.id).all()
            if diseases:
                print(f"First disease: {diseases[0]}")
        except Exception as e:
            print(f"Error querying/serializing diseases: {e}")
            
    else:
        print("No animals found.")
