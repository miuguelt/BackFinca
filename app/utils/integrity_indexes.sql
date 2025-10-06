-- Índices optimizados para consultas de integridad referencial
-- Estos índices mejoran el rendimiento de las verificaciones de dependencias

-- Índices para verificaciones de dependencias inversas (otros registros que apuntan a este)
-- Patrones: WHERE foreign_key_field = record_id

-- Animals - Referencias desde otros animales (padre/madre)
CREATE INDEX IF NOT EXISTS ix_animals_idfather ON animals(idFather);
CREATE INDEX IF NOT EXISTS ix_animals_idmother ON animals(idMother);

-- Breeds - Referencias desde animales
CREATE INDEX IF NOT EXISTS ix_animals_breeds_id_integrity ON animals(breeds_id);

-- Species - Referencias desde breeds
CREATE INDEX IF NOT EXISTS ix_breeds_species_id_integrity ON breeds(species_id);

-- Treatments - Referencias desde animals
CREATE INDEX IF NOT EXISTS ix_treatments_animals_id_integrity ON treatments(animals_id);

-- Vaccinations - Referencias desde animals
CREATE INDEX IF NOT EXISTS ix_vaccinations_animals_id_integrity ON vaccinations(animals_id);

-- AnimalDiseases - Referencias desde animals y diseases
CREATE INDEX IF NOT EXISTS ix_animal_diseases_animal_id_integrity ON animal_diseases(animal_id);
CREATE INDEX IF NOT EXISTS ix_animal_diseases_disease_id_integrity ON animal_diseases(disease_id);

-- Control - Referencias desde animals
CREATE INDEX IF NOT EXISTS ix_control_animals_id_integrity ON control(animals_id);

-- AnimalFields - Referencias desde animals y fields
CREATE INDEX IF NOT EXISTS ix_animal_fields_animal_id_integrity ON animal_fields(animal_id);
CREATE INDEX IF NOT EXISTS ix_animal_fields_field_id_integrity ON animal_fields(field_id);

-- GeneticImprovements - Referencias desde animals
CREATE INDEX IF NOT EXISTS ix_genetic_improvements_animals_id_integrity ON genetic_improvements(animals_id);

-- TreatmentMedications - Referencias desde treatments y medications
CREATE INDEX IF NOT EXISTS ix_treatment_medications_treatment_id_integrity ON treatment_medications(treatment_id);
CREATE INDEX IF NOT EXISTS ix_treatment_medications_medication_id_integrity ON treatment_medications(medication_id);

-- TreatmentVaccines - Referencias desde treatments y vaccines
CREATE INDEX IF NOT EXISTS ix_treatment_vaccines_treatment_id_integrity ON treatment_vaccines(treatment_id);
CREATE INDEX IF NOT EXISTS ix_treatment_vaccines_vaccine_id_integrity ON treatment_vaccines(vaccine_id);

-- Índices compuestos para consultas frecuentes de integridad
-- Patrones: WHERE table_id = record_id AND other_conditions

-- Para verificaciones rápidas de animales activos vs dependencias
CREATE INDEX IF NOT EXISTS ix_animals_status_breeds_id ON animals(status, breeds_id);

-- Para tratamientos por animal y fecha (verificaciones de integridad temporal)
CREATE INDEX IF NOT EXISTS ix_treatments_animals_date ON treatments(animals_id, treatment_date);

-- Para vacunaciones por animal y fecha
CREATE INDEX IF NOT EXISTS ix_vaccinations_animals_date ON vaccinations(animals_id, vaccination_date);

-- Para controles por animal y fecha
CREATE INDEX IF NOT EXISTS ix_control_animals_date ON control(animals_id, checkup_date);

-- Índices de cobertura para consultas EXISTS optimizadas
-- Estos índices permiten que las consultas EXISTS sean más rápidas

-- Índices de solo lectura para verificaciones de integridad (PostgreSQL 11+)
-- CREATE INDEX IF NOT EXISTS ix_animals_idfather_covering ON animals(idFather) INCLUDE (id);
-- CREATE INDEX IF NOT EXISTS ix_animals_idmother_covering ON animals(idMother) INCLUDE (id);
-- CREATE INDEX IF NOT EXISTS ix_animals_breeds_id_covering ON animals(breeds_id) INCLUDE (id);

-- Índices compuestos adicionales para consultas UNION ALL de integridad
-- Optimizan el batch checking de múltiples dependencias

CREATE INDEX IF NOT EXISTS ix_animals_integrity_batch ON animals(idFather, idMother, breeds_id);
CREATE INDEX IF NOT EXISTS ix_treatments_integrity_batch ON treatments(animals_id, treatment_date);
CREATE INDEX IF NOT EXISTS ix_vaccinations_integrity_batch ON vaccinations(animals_id, vaccination_date);
CREATE INDEX IF NOT EXISTS ix_control_integrity_batch ON control(animals_id, checkup_date);

-- Índices para tablas de relación muchos-a-muchos (integridad referencial)
CREATE INDEX IF NOT EXISTS ix_animal_diseases_integrity_batch ON animal_diseases(animal_id, disease_id);
CREATE INDEX IF NOT EXISTS ix_animal_fields_integrity_batch ON animal_fields(animal_id, field_id);
CREATE INDEX IF NOT EXISTS ix_treatment_medications_integrity_batch ON treatment_medications(treatment_id, medication_id);
CREATE INDEX IF NOT EXISTS ix_treatment_vaccines_integrity_batch ON treatment_vaccines(treatment_id, vaccine_id);

-- Nota: Los índices de cobertura (INCLUDE) son específicos de PostgreSQL 11+
-- Para MySQL/MariaDB, los índices compuestos son suficientes
-- Para SQLite, los índices simples proporcionan la mayor parte del beneficio

-- Estadísticas para optimización del query planner
-- ANALYZE animals;
-- ANALYZE breeds;
-- ANALYZE species;
-- ANALYZE treatments;
-- ANALYZE vaccinations;
-- ANALYZE animal_diseases;
-- ANALYZE control;
-- ANALYZE animal_fields;
-- ANALYZE genetic_improvements;
-- ANALYZE treatment_medications;
-- ANALYZE treatment_vaccines;