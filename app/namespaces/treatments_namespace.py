# app/namespaces/treatments_namespace.py

import logging

from app.models.treatments import Treatments
from app.utils.namespace_helpers import create_optimized_namespace


logger = logging.getLogger(__name__)


treatments_ns = create_optimized_namespace(
    name='treatments',
    description='Tratamientos médicos',
    model_class=Treatments,
    path='/treatments'
)
