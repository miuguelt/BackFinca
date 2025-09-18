
import os
# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
# Force remote DB URI
os.environ['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://fincau:fincac@isladigital.xyz:3311/finca'

from app import create_app, db
from faker import Faker
from datetime import datetime, timedelta
import random

print('[SEED] ENV SQLALCHEMY_DATABASE_URI =', os.getenv('SQLALCHEMY_DATABASE_URI'))
app = create_app('development')
print('[SEED] app.config[SQLALCHEMY_DATABASE_URI] =', app.config.get('SQLALCHEMY_DATABASE_URI'))
fake = Faker('es_ES')

with app.app_context():
    db.drop_all(); db.create_all()
    # Importar modelos
    from app.models.user import User, Role
    from app.models.animals import Animals
    from app.models.fields import Fields
    from app.models.breeds import Breeds
    from app.models.species import Species
    from app.models.medications import Medications
    from app.models.vaccines import Vaccines
    from app.models.vaccinations import Vaccinations
    from app.models.treatments import Treatments
    from app.models.diseases import Diseases
    from app.models.control import Control
    from app.models.foodTypes import FoodTypes
    from app.models.geneticImprovements import GeneticImprovements
    # Crear especies y razas (con nombres únicos)
    species_list = []
    used_species_names = set()
    for i in range(5):
        name = fake.word()
        while name in used_species_names:
            name = fake.word()
        used_species_names.add(name)
        sp = Species(name=name)
        db.session.add(sp)
        species_list.append(sp)
    db.session.commit()
    
    breeds_list = []
    used_breed_names = set()
    for i in range(10):
        name = fake.word()
        while name in used_breed_names:
            name = fake.word()
        used_breed_names.add(name)
        br = Breeds(name=name, species_id=random.choice(species_list).id)
        db.session.add(br)
        breeds_list.append(br)
    db.session.commit()
    
    # Usuarios (con IDs únicos)
    for i in range(40):
        u = User(
            identification=20000000+i,  # Start from 20M to avoid conflicts
            fullname=fake.name(),
            password=fake.password(),
            email=fake.unique.email(),
            phone=fake.phone_number(),
            role=random.choice(list(Role)),
            status=True
        )
        db.session.add(u)
    db.session.commit()
    
    # Campos (con nombres únicos)
    used_field_names = set()
    for i in range(40):
        name = f"{fake.word()}_{i}"  # Add index to ensure uniqueness
        while name in used_field_names:
            name = f"{fake.word()}_{i}_{random.randint(1, 999)}"
        used_field_names.add(name)
        f = Fields(
            name=name,
            area=random.randint(1,100),
            ubication=fake.city(),
            capacity=random.randint(10,100),
            handlings=fake.word(),
            gauges=fake.word(),
            state='Disponible'
        )
        db.session.add(f)
    db.session.commit()
    # Animales
    for i in range(40):
        a = Animals(
            name=fake.first_name(),
            birth_date=fake.date_between('-5y','-1y'),
            breed_id=random.choice(breeds_list).id,
            field_id=random.randint(1,40),
            status='Sano'
        )
        db.session.add(a)
    db.session.commit()
    # Medicamentos (con nombres únicos)
    used_medication_names = set()
    for i in range(40):
        name = f"{fake.word()}_{i}"
        while name in used_medication_names:
            name = f"{fake.word()}_{i}_{random.randint(1, 999)}"
        used_medication_names.add(name)
        m = Medications(
            name=name,
            description=fake.sentence(),
            indications=fake.sentence(),
            route_administration_id=random.randint(1, 4),  # Reference to route_administrations table
            availability=True
        )
        db.session.add(m)
    db.session.commit()
    # Vacunas (con nombres únicos)
    used_vaccine_names = set()
    for i in range(40):
        name = f"{fake.word()}_{i}"
        while name in used_vaccine_names:
            name = f"{fake.word()}_{i}_{random.randint(1, 999)}"
        used_vaccine_names.add(name)
        v = Vaccines(
            name=name,
            description=fake.sentence(),
            indications=fake.sentence()
        )
        db.session.add(v)
    db.session.commit()
    # Vacunaciones
    for i in range(40):
        vac = Vaccinations(
            vaccination_date=fake.date_between('-2y','today'),
            vaccine_id=random.randint(1,40),
            animal_id=random.randint(1,40),
            instructor_id=random.randint(1,40)
        )
        db.session.add(vac)
    db.session.commit()
    # Tratamientos
    for i in range(40):
        t = Treatments(
            treatment_date=fake.date_between('-2y','today'),
            animal_id=random.randint(1,40),
            description=fake.sentence()
        )
        db.session.add(t)
    db.session.commit()
    # Enfermedades (con nombres únicos)
    used_disease_names = set()
    for i in range(40):
        name = f"{fake.word()}_{i}"
        while name in used_disease_names:
            name = f"{fake.word()}_{i}_{random.randint(1, 999)}"
        used_disease_names.add(name)
        d = Diseases(
            name=name,
            description=fake.sentence()
        )
        db.session.add(d)
    db.session.commit()
    # Controles
    for i in range(40):
        c = Control(
            animal_id=random.randint(1,40),
            checkup_date=fake.date_between('-1y','today'),
            weight=random.randint(100,500),
            height=random.randint(100,200),
            health_status='Bueno',
            description=fake.sentence()
        )
        db.session.add(c)
    db.session.commit()
    # Tipos de alimento (con nombres únicos)
    used_food_names = set()
    for i in range(40):
        name = f"{fake.word()}_{i}"
        while name in used_food_names:
            name = f"{fake.word()}_{i}_{random.randint(1, 999)}"
        used_food_names.add(name)
        ft = FoodTypes(
            name=name,
            description=fake.sentence()
        )
        db.session.add(ft)
    db.session.commit()
    # Mejoramientos genéticos (con nombres únicos)
    used_genetic_names = set()
    for i in range(40):
        name = f"{fake.word()}_{i}"
        while name in used_genetic_names:
            name = f"{fake.word()}_{i}_{random.randint(1, 999)}"
        used_genetic_names.add(name)
        gi = GeneticImprovements(
            name=name,
            description=fake.sentence()
        )
        db.session.add(gi)
    db.session.commit()
    print('Seed masivo completado: 40 registros por tabla principal.')
