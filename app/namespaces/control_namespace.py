# app/namespaces/control_namespace.py

from app.models.control import Control
from app.utils.namespace_helpers import create_optimized_namespace

# Create the optimized namespace for the Control model
control_ns = create_optimized_namespace(
    name='controls',
    description='🩺 Gestión de Controles de Salud',
    model_class=Control,
    path='/controls'
)
