"""
add additional performance indexes across frequently filtered/sorted fields

Revision ID: 20250906_more_idx
Revises: 20250906_norm_food_type
Create Date: 2025-09-06
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250906_more_idx'
down_revision = '20250906_norm_food_type'
branch_labels = None
depends_on = None


def upgrade():
    # animals
    op.create_index('ix_animals_status', 'animals', ['status'], unique=False)

    # user
    op.create_index('ix_user_role', 'user', ['role'], unique=False)
    op.create_index('ix_user_status', 'user', ['status'], unique=False)
    op.create_index('ix_user_created_at', 'user', ['created_at'], unique=False)

    # vaccines
    op.create_index('ix_vaccines_target_disease_id', 'vaccines', ['target_disease_id'], unique=False)
    op.create_index('ix_vaccines_type', 'vaccines', ['type'], unique=False)
    op.create_index('ix_vaccines_route_administration_id', 'vaccines', ['route_administration_id'], unique=False)
    op.create_index('ix_vaccines_created_at', 'vaccines', ['created_at'], unique=False)

    # vaccinations
    op.create_index('ix_vaccinations_vaccine_id', 'vaccinations', ['vaccine_id'], unique=False)
    op.create_index('ix_vaccinations_apprentice_id', 'vaccinations', ['apprentice_id'], unique=False)
    op.create_index('ix_vaccinations_instructor_id', 'vaccinations', ['instructor_id'], unique=False)

    # treatment_medications
    op.create_index('ix_treatment_medications_treatment_id', 'treatment_medications', ['treatment_id'], unique=False)
    op.create_index('ix_treatment_medications_medication_id', 'treatment_medications', ['medication_id'], unique=False)

    # treatment_vaccines
    op.create_index('ix_treatment_vaccines_treatment_id', 'treatment_vaccines', ['treatment_id'], unique=False)
    op.create_index('ix_treatment_vaccines_vaccine_id', 'treatment_vaccines', ['vaccine_id'], unique=False)

    # medications
    op.create_index('ix_medications_route_administration_id', 'medications', ['route_administration_id'], unique=False)
    op.create_index('ix_medications_availability', 'medications', ['availability'], unique=False)
    op.create_index('ix_medications_created_at', 'medications', ['created_at'], unique=False)

    # route_administrations
    op.create_index('ix_route_administrations_status', 'route_administrations', ['status'], unique=False)
    op.create_index('ix_route_administrations_created_at', 'route_administrations', ['created_at'], unique=False)

    # fields
    op.create_index('ix_fields_state', 'fields', ['state'], unique=False)
    op.create_index('ix_fields_food_type_id', 'fields', ['food_type_id'], unique=False)
    op.create_index('ix_fields_created_at', 'fields', ['created_at'], unique=False)

    # food_types
    op.create_index('ix_food_types_sowing_date', 'food_types', ['sowing_date'], unique=False)
    op.create_index('ix_food_types_harvest_date', 'food_types', ['harvest_date'], unique=False)
    op.create_index('ix_food_types_area', 'food_types', ['area'], unique=False)
    op.create_index('ix_food_types_created_at', 'food_types', ['created_at'], unique=False)

    # animal_diseases
    op.create_index('ix_animal_diseases_animal_diagnosis', 'animal_diseases', ['animal_id', 'diagnosis_date'], unique=False)
    op.create_index('ix_animal_diseases_disease_id', 'animal_diseases', ['disease_id'], unique=False)
    op.create_index('ix_animal_diseases_instructor_id', 'animal_diseases', ['instructor_id'], unique=False)
    op.create_index('ix_animal_diseases_status', 'animal_diseases', ['status'], unique=False)
    op.create_index('ix_animal_diseases_created_at', 'animal_diseases', ['created_at'], unique=False)

    # genetic_improvements
    op.create_index('ix_genetic_improvements_animal_date', 'genetic_improvements', ['animal_id', 'date'], unique=False)
    op.create_index('ix_genetic_improvements_created_at', 'genetic_improvements', ['created_at'], unique=False)

    # control
    op.create_index('ix_control_health_status', 'control', ['health_status'], unique=False)

    # breeds
    op.create_index('ix_breeds_species_id', 'breeds', ['species_id'], unique=False)
    op.create_index('ix_breeds_created_at', 'breeds', ['created_at'], unique=False)

    # species
    op.create_index('ix_species_created_at', 'species', ['created_at'], unique=False)

    # animal_fields
    op.create_index('ix_animal_fields_animal_assignment', 'animal_fields', ['animal_id', 'assignment_date'], unique=False)
    op.create_index('ix_animal_fields_field_id', 'animal_fields', ['field_id'], unique=False)
    op.create_index('ix_animal_fields_created_at', 'animal_fields', ['created_at'], unique=False)

    # diseases
    op.create_index('ix_diseases_created_at', 'diseases', ['created_at'], unique=False)


def downgrade():
    # diseases
    op.drop_index('ix_diseases_created_at', table_name='diseases')

    # animal_fields
    op.drop_index('ix_animal_fields_created_at', table_name='animal_fields')
    op.drop_index('ix_animal_fields_field_id', table_name='animal_fields')
    op.drop_index('ix_animal_fields_animal_assignment', table_name='animal_fields')

    # species
    op.drop_index('ix_species_created_at', table_name='species')

    # breeds
    op.drop_index('ix_breeds_created_at', table_name='breeds')
    op.drop_index('ix_breeds_species_id', table_name='breeds')

    # control
    op.drop_index('ix_control_health_status', table_name='control')

    # genetic_improvements
    op.drop_index('ix_genetic_improvements_created_at', table_name='genetic_improvements')
    op.drop_index('ix_genetic_improvements_animal_date', table_name='genetic_improvements')

    # animal_diseases
    op.drop_index('ix_animal_diseases_created_at', table_name='animal_diseases')
    op.drop_index('ix_animal_diseases_status', table_name='animal_diseases')
    op.drop_index('ix_animal_diseases_instructor_id', table_name='animal_diseases')
    op.drop_index('ix_animal_diseases_disease_id', table_name='animal_diseases')
    op.drop_index('ix_animal_diseases_animal_diagnosis', table_name='animal_diseases')

    # food_types
    op.drop_index('ix_food_types_created_at', table_name='food_types')
    op.drop_index('ix_food_types_area', table_name='food_types')
    op.drop_index('ix_food_types_harvest_date', table_name='food_types')
    op.drop_index('ix_food_types_sowing_date', table_name='food_types')

    # fields
    op.drop_index('ix_fields_created_at', table_name='fields')
    op.drop_index('ix_fields_food_type_id', table_name='fields')
    op.drop_index('ix_fields_state', table_name='fields')

    # route_administrations
    op.drop_index('ix_route_administrations_created_at', table_name='route_administrations')
    op.drop_index('ix_route_administrations_status', table_name='route_administrations')

    # medications
    op.drop_index('ix_medications_created_at', table_name='medications')
    op.drop_index('ix_medications_availability', table_name='medications')
    op.drop_index('ix_medications_route_administration_id', table_name='medications')

    # treatment_vaccines
    op.drop_index('ix_treatment_vaccines_vaccine_id', table_name='treatment_vaccines')
    op.drop_index('ix_treatment_vaccines_treatment_id', table_name='treatment_vaccines')

    # treatment_medications
    op.drop_index('ix_treatment_medications_medication_id', table_name='treatment_medications')
    op.drop_index('ix_treatment_medications_treatment_id', table_name='treatment_medications')

    # vaccinations
    op.drop_index('ix_vaccinations_instructor_id', table_name='vaccinations')
    op.drop_index('ix_vaccinations_apprentice_id', table_name='vaccinations')
    op.drop_index('ix_vaccinations_vaccine_id', table_name='vaccinations')

    # vaccines
    op.drop_index('ix_vaccines_created_at', table_name='vaccines')
    op.drop_index('ix_vaccines_route_administration_id', table_name='vaccines')
    op.drop_index('ix_vaccines_type', table_name='vaccines')
    op.drop_index('ix_vaccines_target_disease_id', table_name='vaccines')

    # user
    op.drop_index('ix_user_created_at', table_name='user')
    op.drop_index('ix_user_status', table_name='user')
    op.drop_index('ix_user_role', table_name='user')

    # animals
    op.drop_index('ix_animals_status', table_name='animals')