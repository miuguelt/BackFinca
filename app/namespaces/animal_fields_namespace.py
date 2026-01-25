from flask_restx import Resource, Namespace, fields
import jwt
from flask import request, jsonify
from datetime import datetime
from app.models.animalFields import AnimalFields
from app.models.animals import Animals  # Corregido: Animals en lugar de Animal
from app.models.fields import Fields  # Corregido: Fields en lugar de Field
from app import db
from app.utils.namespace_helpers import create_optimized_namespace, _cache_clear
from app.utils.response_handler import APIResponse

animal_fields_ns = create_optimized_namespace(
    name='AnimalFields',
    description='Operaciones CRUD para campos de animales',
    model_class=AnimalFields,
    path='/animal-fields'
)

# Note: Standard CRUD operations (GET list, GET by ID, POST, PUT, PATCH, DELETE) 
# are automatically handled by create_optimized_namespace above.
# Use this file only for custom non-standard endpoints if needed.

