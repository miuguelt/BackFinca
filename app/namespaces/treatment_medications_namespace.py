# app/namespaces/treatment_medications_namespace.py

from app.models.treatment_medications import TreatmentMedications
from app.utils.namespace_helpers import create_optimized_namespace

# Create the optimized namespace for the TreatmentMedications model
treatment_medications_ns = create_optimized_namespace(
    name='treatment-medications',
    description='🔗 Gestión de Medicamentos por Tratamiento',
    model_class=TreatmentMedications,
    path='/treatment-medications'
)
