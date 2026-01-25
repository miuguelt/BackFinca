from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_current_user
from flask_restx import Resource, Namespace, fields
from app import db, models
from app.utils.response_handler import APIResponse
from app.utils.namespace_helpers import create_optimized_namespace, _cache_clear

model_for_update = models.AnimalDisease.__table__.columns.keys()

animal_diseases_ns = create_optimized_namespace('animal-diseases', description='Gestión de enfermedades de animales', model_class=models.AnimalDisease)

# Note: Standard CRUD operations (GET list, GET by ID, POST, PUT, PATCH, DELETE) 
# are automatically handled by create_optimized_namespace above.
# This file is intentionally minimal as all logic is in the optimized helper.

