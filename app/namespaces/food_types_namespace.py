# app/namespaces/food_types_namespace.py

from app.models.foodTypes import FoodTypes
from app.utils.namespace_helpers import create_optimized_namespace

# Create the optimized namespace for the FoodTypes model
# Use underscore path/name to stay compatible with tests and older clients
food_types_ns = create_optimized_namespace(
    name='food_types',
    description='🌾 Gestión de Tipos de Alimentación',
    model_class=FoodTypes,
    path='/food_types'
)
