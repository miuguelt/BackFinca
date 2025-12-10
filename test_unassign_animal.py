
import pytest
from app import create_app, db
from app.models.fields import Fields
from app.models.animals import Animals, Sex, AnimalStatus
from app.models.breeds import Breeds
from app.models.species import Species
from app.models.animalFields import AnimalFields
from datetime import date
from flask_jwt_extended import create_access_token

@pytest.fixture
def app():
    app = create_app('testing')
    app.config['JWT_SECRET_KEY'] = 'testing_secret'
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_headers(app):
    with app.app_context():
        access_token = create_access_token(identity='1')
    return {'Authorization': f'Bearer {access_token}'}

def test_unassign_animal_from_field(client, auth_headers):
    # Setup
    species = Species(name="Bovino")
    db.session.add(species)
    db.session.commit()
    breed = Breeds(name="Brahman", species_id=species.id)
    db.session.add(breed)
    db.session.commit()
    field = Fields(name="Field A", area="10", state="Activo")
    db.session.add(field)
    db.session.commit()
    animal = Animals(record="A001", sex=Sex.Hembra, weight=300, birth_date=date.today(), breeds_id=breed.id)
    db.session.add(animal)
    db.session.commit()

    # Assign to field
    af = AnimalFields(animal_id=animal.id, field_id=field.id, assignment_date=date.today())
    db.session.add(af)
    db.session.commit()

    # Verify assignment exists and is active
    assert af.removal_date is None

    # Test Unassign (field_id: null)
    payload = {
        "field_id": None
    }
    response = client.put(f'/api/v1/animals/{animal.id}', json=payload, headers=auth_headers)
    
    assert response.status_code == 200
    
    # Reload assignment from DB
    db.session.expire(af)
    af = AnimalFields.query.get(af.id)
    
    # Verify removal_date is set to today
    assert af.removal_date == date.today()
    assert response.get_json()['success'] is True
