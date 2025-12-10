
import pytest
from app import create_app, db
from app.models.fields import Fields
from app.models.animals import Animals, Sex, AnimalStatus
from app.models.breeds import Breeds
from app.models.species import Species
from app.models.animalFields import AnimalFields
from datetime import date, timedelta
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

def test_add_animal_to_field_success(client, auth_headers):
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

    # Test
    payload = {
        "field_id": field.id,
        "animal_id": animal.id,
        "assignment_date": date.today().isoformat(),
        "notes": "Initial assignment"
    }
    response = client.post('/api/v1/animal-fields', json=payload, headers=auth_headers)
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['success'] is True
    assert "asignado al potrero exitosamente" in data['message']

def test_add_animal_to_field_conflict(client, auth_headers):
    # Setup
    species = Species(name="Bovino")
    db.session.add(species)
    db.session.commit()
    breed = Breeds(name="Brahman", species_id=species.id)
    db.session.add(breed)
    db.session.commit()
    field_a = Fields(name="Field A", area="10", state="Activo")
    field_b = Fields(name="Field B", area="10", state="Activo")
    db.session.add_all([field_a, field_b])
    db.session.commit()
    animal = Animals(record="A001", sex=Sex.Hembra, weight=300, birth_date=date.today(), breeds_id=breed.id)
    db.session.add(animal)
    db.session.commit()

    # Initial Assignment (directly to DB for setup)
    af = AnimalFields(animal_id=animal.id, field_id=field_a.id, assignment_date=date.today())
    db.session.add(af)
    db.session.commit()

    # Test Conflict
    payload = {
        "field_id": field_b.id,
        "animal_id": animal.id,
        "assignment_date": date.today().isoformat(),
        "notes": "Try valid assignment"
    }
    response = client.post('/api/v1/animal-fields', json=payload, headers=auth_headers)
    
    assert response.status_code == 409
    data = response.get_json()
    assert data['success'] is False
    assert "ya está en el potrero 'Field A'" in data['error']['message']
    assert data['error']['details']['current_field_id'] == field_a.id

def test_add_animal_to_field_not_found(client, auth_headers):
    payload = {
        "field_id": 999,
        "animal_id": 999,
        "assignment_date": date.today().isoformat()
    }
    response = client.post('/api/v1/animal-fields', json=payload, headers=auth_headers)
    assert response.status_code == 404
