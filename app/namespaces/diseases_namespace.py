# app/namespaces/diseases_namespace.py

from app.models.diseases import Diseases
from app.utils.namespace_helpers import create_optimized_namespace

# Create the optimized namespace for the Diseases model
diseases_ns = create_optimized_namespace(
    name='diseases',
    description='🦠 Gestión de Enfermedades',
    model_class=Diseases,
    path='/diseases'
)
