# app/namespaces/genetic_improvements_namespace.py

from app.models.geneticImprovements import GeneticImprovements
from app.utils.namespace_helpers import create_optimized_namespace

# Create the optimized namespace for the GeneticImprovements model
genetic_improvements_ns = create_optimized_namespace(
    name='genetic-improvements',
    description='🧬 Gestión de Mejoras Genéticas',
    model_class=GeneticImprovements,
    path='/genetic-improvements'
)
