# app/namespaces/fields_namespace.py

from app.models.fields import Fields
from app.utils.namespace_helpers import create_optimized_namespace

# Create the optimized namespace for the Fields model
fields_ns = create_optimized_namespace(
    name='fields',
    description='🏞️ Gestión de Campos y Potreros',
    model_class=Fields,
    path='/fields'
)
