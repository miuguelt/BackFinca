
import sys
import os
from datetime import date
import logging

# Add app to path
sys.path.append(os.getcwd())

from flask import Flask
from app import db
from app.models.treatments import Treatments
from app.models.base_model import ValidationError

# Configurar logging para ver warnings
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
# Configure minimal DB (sqlite in memory)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def test_validation():
    with app.app_context():
        db.create_all()

        from datetime import date
        
        # INVALID payload (missing description)
        payload = {
            'treatment_date': date(2026, 1, 22), 
            'description': '',  # Empty
            'frequency': 'Daily', 
            'dosis': '10ml',
            'animal_id': 1
        }
        
        print(f"Testing with INVALID payload: {payload}")
        
        try:
            # Check model columns
            print(f"Model columns: {[c.name for c in Treatments.__table__.columns]}")
            print(f"Required fields: {Treatments._required_fields}")
            
            instance = Treatments.create(**payload)
            print("Validation successful! (Unexpected)")
            print(f"Instance created: {instance}")
        except ValidationError as e:
            print("Caught ValidationError (Expected):")
            print(e.message)
            if hasattr(e, 'errors'):
                print(f"Errors: {e.errors}")
        except Exception as e:
            print(f"Caught unexpected exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_validation()
