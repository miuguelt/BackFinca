
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
    app.config['JWT_SECRET_KEY'] = 'testing_secret'  # Ensure secret is set
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
        access_token = create_access_token(identity='1') # Identity usually is user id
    return {'Authorization': f'Bearer {access_token}'}

def test_get_animals_in_field(client, auth_headers):
    # Setup data
    species = Species(name="Bovino")
    db.session.add(species)
    db.session.commit()
    
    breed = Breeds(name="Brahman", species_id=species.id)
    db.session.add(breed)
    db.session.commit()
    
    field = Fields(name="Test Field", area="10", state="Activo")
    db.session.add(field)
    db.session.commit()
    
    animal1 = Animals(
        record="A001", 
        sex=Sex.Hembra, 
        weight=300, 
        birth_date=date.today() - timedelta(days=365),
        status=AnimalStatus.Vivo,
        breeds_id=breed.id
    )
    animal2 = Animals(
        record="A002", 
        sex=Sex.Macho, 
        weight=400, 
        birth_date=date.today() - timedelta(days=730),
        status=AnimalStatus.Vivo,
        breeds_id=breed.id
    )
    # Animal not in field
    animal3 = Animals(
        record="A003", 
        sex=Sex.Hembra, 
        weight=350, 
        birth_date=date.today() - timedelta(days=500),
        status=AnimalStatus.Vivo,
        breeds_id=breed.id
    )
    
    db.session.add_all([animal1, animal2, animal3])
    db.session.commit()
    
    # Assign animals to field
    af1 = AnimalFields(animal_id=animal1.id, field_id=field.id, assignment_date=date.today())
    af2 = AnimalFields(animal_id=animal2.id, field_id=field.id, assignment_date=date.today())
    
    db.session.add_all([af1, af2])
    db.session.commit()
    
    # Test endpoint
    response = client.get(f'/api/v1/fields/{field.id}/animals', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert len(data['data']) == 2
    
    records = [a['record'] for a in data['data']]
    assert "A001" in records
    assert "A002" in records
    assert "A003" not in records
    
    # Check computed fields
    assert 'age_in_months' in data['data'][0]
    assert 'is_adult' in data['data'][0]

def test_get_animals_in_empty_field(client, auth_headers):
    field = Fields(name="Empty Field", area="5", state="Activo")
    db.session.add(field)
    db.session.commit()
    
    response = client.get(f'/api/v1/fields/{field.id}/animals', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert len(data['data']) == 0

def test_get_animals_in_nonexistent_field(client, auth_headers):
    response = client.get('/api/v1/fields/999/animals', headers=auth_headers)
    assert response.status_code == 404
