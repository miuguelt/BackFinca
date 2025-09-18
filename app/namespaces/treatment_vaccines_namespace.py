# app/namespaces/treatment_vaccines_namespace.py

from app.models.treatment_vaccines import TreatmentVaccines
from app.utils.namespace_helpers import create_optimized_namespace

# Create the optimized namespace for the TreatmentVaccines model
treatment_vaccines_ns = create_optimized_namespace(
    name='treatment-vaccines',
    description='🔗 Gestión de Vacunas por Tratamiento',
    model_class=TreatmentVaccines,
    path='/treatment-vaccines'
)
