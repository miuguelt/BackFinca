-- ====================================================================
-- Migración: Agregar índices de rendimiento en updated_at y created_at
-- Fecha: 2025-10-05
-- Descripción: Mejora velocidad de queries con ?since= y /metadata endpoints
-- ====================================================================

-- User table
CREATE INDEX ix_user_updated_at ON user(updated_at);
CREATE INDEX ix_user_created_at ON user(created_at);

-- Animals table (updated_at solo, ya tiene created_at)
CREATE INDEX ix_animals_updated_at ON animals(updated_at);

-- Diseases table
CREATE INDEX ix_diseases_updated_at ON diseases(updated_at);
CREATE INDEX ix_diseases_created_at ON diseases(created_at);

-- Breeds table
CREATE INDEX ix_breeds_updated_at ON breeds(updated_at);
CREATE INDEX ix_breeds_created_at ON breeds(created_at);

-- Species table
CREATE INDEX ix_species_updated_at ON species(updated_at);
CREATE INDEX ix_species_created_at ON species(created_at);

-- Medications table
CREATE INDEX ix_medications_updated_at ON medications(updated_at);
CREATE INDEX ix_medications_created_at ON medications(created_at);

-- Vaccines table
CREATE INDEX ix_vaccines_updated_at ON vaccines(updated_at);
CREATE INDEX ix_vaccines_created_at ON vaccines(created_at);

-- Treatments table
CREATE INDEX ix_treatments_updated_at ON treatments(updated_at);
CREATE INDEX ix_treatments_created_at ON treatments(created_at);

-- Vaccinations table
CREATE INDEX ix_vaccinations_updated_at ON vaccinations(updated_at);
CREATE INDEX ix_vaccinations_created_at ON vaccinations(created_at);

-- Control table
CREATE INDEX ix_control_updated_at ON control(updated_at);
CREATE INDEX ix_control_created_at ON control(created_at);

-- Fields table
CREATE INDEX ix_fields_updated_at ON fields(updated_at);
CREATE INDEX ix_fields_created_at ON fields(created_at);

-- Food types table
CREATE INDEX ix_food_types_updated_at ON food_types(updated_at);
CREATE INDEX ix_food_types_created_at ON food_types(created_at);

-- AnimalDiseases table (junction table)
CREATE INDEX ix_animal_diseases_updated_at ON animal_diseases(updated_at);
CREATE INDEX ix_animal_diseases_created_at ON animal_diseases(created_at);

-- AnimalFields table (junction table)
CREATE INDEX ix_animal_fields_updated_at ON animal_fields(updated_at);
CREATE INDEX ix_animal_fields_created_at ON animal_fields(created_at);

-- Genetic Improvements table
CREATE INDEX ix_genetic_improvements_updated_at ON genetic_improvements(updated_at);
CREATE INDEX ix_genetic_improvements_created_at ON genetic_improvements(created_at);

-- Route Administration table
CREATE INDEX ix_route_administration_updated_at ON route_administration(updated_at);
CREATE INDEX ix_route_administration_created_at ON route_administration(created_at);

-- Treatment Medications table
CREATE INDEX ix_treatment_medications_updated_at ON treatment_medications(updated_at);
CREATE INDEX ix_treatment_medications_created_at ON treatment_medications(created_at);

-- Treatment Vaccines table
CREATE INDEX ix_treatment_vaccines_updated_at ON treatment_vaccines(updated_at);
CREATE INDEX ix_treatment_vaccines_created_at ON treatment_vaccines(created_at);

SELECT 'Performance indexes created successfully!' AS STATUS;
