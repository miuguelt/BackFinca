# Exponer modelos principales con alias que coinciden con nombres esperados por pruebas
from .base_model import BaseModel
from .user import User
from .animals import Animals as Animal
from .species import Species
from .breeds import Breeds as Breed
from .fields import Fields as Field
from .diseases import Diseases as Disease
from .animalDiseases import AnimalDiseases as AnimalDisease
from .animalFields import AnimalFields as AnimalField
from .vaccinations import Vaccinations as Vaccination
from .vaccines import Vaccines as Vaccine
from .medications import Medications as Medication
from .treatments import Treatments as Treatment
from .treatment_medications import TreatmentMedications as TreatmentMedication
from .treatment_vaccines import TreatmentVaccines as TreatmentVaccine
from .control import Control
from .foodTypes import FoodTypes as FoodType
from .geneticImprovements import GeneticImprovements as GeneticImprovement
from .route_administration import RouteAdministration

__all__ = [
    'BaseModel',
    'User',
    'Animal',
    'Species',
    'Breed',
    'Field',
    'Disease',
    'AnimalDisease',
    'AnimalField',
    'Vaccination',
    'Vaccine',
    'Medication',
    'Treatment',
    'TreatmentMedication',
    'TreatmentVaccine',
    'Control',
    'FoodType',
    'GeneticImprovement',
    'RouteAdministration',
]