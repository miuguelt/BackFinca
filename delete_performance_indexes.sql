-- Índices ultra-optimizados para eliminación de animales
-- Optimizados específicamente para las consultas EXISTS del integrity checker

-- Índices de alto rendimiento para verificación de dependencias
-- Estos índices están optimizados para consultas EXISTS con LIMIT 1

-- Auto-referencias de animales (padre/madre) - las más críticas
CREATE INDEX IF NOT EXISTS ix_animals_idfather_exists ON animals(idFather) INCLUDE (id);
CREATE INDEX IF NOT EXISTS ix_animals_idmother_exists ON animals(idMother) INCLUDE (id);

-- Índices compuestos para verificación batch de animales
CREATE INDEX IF NOT EXISTS ix_animals_parent_check ON animals(idFather, idMother, id);

-- Dependencias directas (tablas hijas)
CREATE INDEX IF NOT EXISTS ix_treatments_animals_id_exists ON treatments(animals_id) INCLUDE (id);
CREATE INDEX IF NOT EXISTS ix_vaccinations_animals_id_exists ON vaccinations(animals_id) INCLUDE (id);
CREATE INDEX IF NOT EXISTS ix_animal_diseases_animal_id_exists ON animal_diseases(animal_id) INCLUDE (id);
CREATE INDEX IF NOT EXISTS ix_control_animals_id_exists ON control(animals_id) INCLUDE (id);
CREATE INDEX IF NOT EXISTS ix_animal_fields_animal_id_exists ON animal_fields(animal_id) INCLUDE (id);
CREATE INDEX IF NOT EXISTS ix_genetic_improvements_animals_id_exists ON genetic_improvements(animals_id) INCLUDE (id);

-- Índices de cobertura para PostgreSQL 11+ (si está disponible)
-- Descomentar si usas PostgreSQL 11+
-- CREATE INDEX IF NOT EXISTS ix_animals_idfather_covering ON animals(idFather) INCLUDE (id, record);
-- CREATE INDEX IF NOT EXISTS ix_animals_idmother_covering ON animals(idMother) INCLUDE (id, record);
-- CREATE INDEX IF NOT EXISTS ix_treatments_animals_id_covering ON treatments(animals_id) INCLUDE (id, treatment_date);

-- Índices para consultas batch (UNION ALL)
CREATE INDEX IF NOT EXISTS ix_animals_batch_delete_check ON animals(id, idFather, idMother, status);

-- Estadísticas actualizadas para el optimizador de consultas
ANALYZE animals;
ANALYZE treatments;
ANALYZE vaccinations;
ANALYZE animal_diseases;
ANALYZE control;
ANALYZE animal_fields;
ANALYZE genetic_improvements;

-- Notas de optimización:
-- 1. Los índices INCLUDE (PostgreSQL) permiten covering indexes para evitar table scans
-- 2. Los índices compuestos optimizan el orden de acceso para consultas batch
-- 3. EXISTS con LIMIT 1 se beneficia enormemente de estos índices
-- 4. El cache del integrity checker (TTL 30s) complementa estos índices