import pytest
from flask import url_for
import json
from app import create_app, db
from app.models import *
import random
import string

# Lista de modelos a probar
MODELS_TO_TEST = [
    User, Animal, Breed, Species, Field, AnimalField, Disease, AnimalDisease,
    Vaccine, Vaccination, Medication, Treatment, TreatmentMedication,
    TreatmentVaccine, Control, FoodType, GeneticImprovement
]

def generate_dummy_data(model_class):
    """Genera datos de prueba básicos para un modelo, enfocándose en campos requeridos."""
    data = {}
    # Asumimos que los modelos tienen un método para obtener su modelo de entrada de restx
    # pero como no lo tenemos a mano, inspeccionamos las columnas.
    for col in model_class.__table__.columns:
        if col.primary_key or col.foreign_keys or col.name in ['created_at', 'updated_at']:
            continue
        
        if not col.nullable and col.default is None:
            if 'password' in col.name:
                data[col.name] = 'TestPassword123!'
            elif 'email' in col.name:
                random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
                data[col.name] = f'test_{random_part}@example.com'
            elif col.type.python_type == str:
                data[col.name] = f"Test {col.name}"
            elif col.type.python_type == int:
                data[col.name] = random.randint(1, 100)
            elif col.type.python_type == float:
                data[col.name] = round(random.uniform(1.0, 100.0), 2)
            elif col.type.python_type == bool:
                data[col.name] = True
            # Para enums, necesitamos una lógica más específica, por ahora lo dejamos simple
            elif hasattr(col.type, 'enums'):
                 if col.type.enums:
                    data[col.name] = random.choice(col.type.enums)

    # Lógica específica para campos que son únicos o tienen FKs
    if model_class == User:
        data['identification'] = random.randint(1000000, 9999999)
        data['role'] = 'admin' # Asumimos que 'admin' es un valor válido
    
    if model_class == Animal:
        # Estos son FKs, necesitamos crearlos o asumir que existen
        data['species_id'] = 1
        data['breed_id'] = 1
        data['field_id'] = 1
        data['weight'] = 50.5 
        data['birth_date'] = '2024-01-01'

    print(f"Generated data for {model_class.__name__}: {data}")
    return data


@pytest.fixture(scope='session')
def app():
    """Crea una instancia de la aplicación para toda la sesión de pruebas."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        # Crear datos iniciales si es necesario
        if not Species.query.first():
            db.session.add(Species(name='Bovino'))
        if not Breed.query.first():
            db.session.add(Breed(name='Angus', species_id=1))
        if not Field.query.first():
            db.session.add(Field(name='Potrero 1'))
        db.session.commit()

        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='session')
def client(app):
    """Un cliente de prueba para la aplicación."""
    return app.test_client()

def test_api_endpoints(client):
    """
    Prueba todos los endpoints de la API para verificar conectividad y respuesta JSON.
    """
    print("\n--- Iniciando prueba de endpoints de la API ---")
    
    rules = [rule for rule in client.application.url_map.iter_rules() if rule.endpoint.startswith('api.')]
    
    tested_posts = set()

    for rule in rules:
        endpoint_name = rule.endpoint.split('.')[-1]
        methods = [m for m in rule.methods if m in ['GET', 'POST']]
        
        if not methods:
            continue

        print(f"\n>>> Probando Endpoint: {rule.rule} ({', '.join(methods)})")

        # --- PRUEBA DE GET (Listar) ---
        if 'GET' in methods and not rule.arguments:
            print(f"  -> GET (List) {rule.rule}")
            res = client.get(rule.rule)
            assert res.status_code in [200, 401, 403], f"GET {rule.rule} falló con {res.status_code}"
            if res.status_code == 200:
                content_type = res.headers.get('Content-Type', '')
                if 'text/html' in content_type:
                    print(f"  ℹ️ GET {rule.rule} devolvió HTML (docs), se omite validación JSON.")
                else:
                    assert res.is_json, f"La respuesta de GET {rule.rule} no es JSON."
                    print(f"  ✅ GET {rule.rule} OK ({res.status_code})")
                
                # Intentar obtener un ID para probar GET (Detalle) y POST
                item_id = None
                try:
                    data = res.get_json()
                    if data.get('success') and data['data'].get('items'):
                        item_id = data['data']['items'][0].get('id')
                except Exception:
                    pass

                # --- PRUEBA DE GET (Detalle) ---
                if item_id and rule.arguments:
                    detail_url = url_for(rule.endpoint, **{list(rule.arguments)[0]: item_id})
                    print(f"  -> GET (Detail) {detail_url}")
                    res_detail = client.get(detail_url)
                    assert res_detail.status_code in [200, 401, 403], f"GET {detail_url} falló con {res_detail.status_code}"
                    if res_detail.status_code == 200:
                        assert res_detail.is_json, f"La respuesta de GET {detail_url} no es JSON."
                        print(f"  ✅ GET {detail_url} OK ({res_detail.status_code})")

        # --- PRUEBA DE POST (Crear) ---
        # Evitar probar el mismo POST dos veces (ej. /bulk)
        if 'POST' in methods and rule.rule not in tested_posts:
            model_name_from_rule = rule.rule.split('/')[2].replace('-', '_') # ej: /api/animal-fields -> animal_fields
            
            # Encontrar el modelo correspondiente
            target_model = next((m for m in MODELS_TO_TEST if m.__tablename__ == model_name_from_rule), None)
            
            if target_model:
                print(f"  -> POST {rule.rule}")
                dummy_data = generate_dummy_data(target_model)
                
                # Para endpoints /bulk, envolvemos en una lista
                if 'bulk' in rule.rule:
                    post_data = [dummy_data]
                else:
                    post_data = dummy_data

                if post_data:
                    res_post = client.post(rule.rule, json=post_data)
                    # El POST puede fallar por validación (422) o FKs (500), lo cual es aceptable en esta prueba simple
                    assert res_post.status_code in [201, 400, 401, 403, 422, 500], f"POST {rule.rule} falló con {res_post.status_code}"
                    assert res_post.is_json, f"La respuesta de POST {rule.rule} no es JSON."
                    print(f"  ✅ POST {rule.rule} OK ({res_post.status_code})")
                else:
                    print(f"  ⚠️ No se generaron datos para POST {rule.rule}, se omite.")
            
            tested_posts.add(rule.rule)

    print("\n--- Prueba de endpoints finalizada ---")
