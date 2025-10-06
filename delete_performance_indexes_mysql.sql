-- Índices ultra-optimizados para eliminación de animales (MySQL)
-- Optimizados específicamente para las consultas EXISTS del integrity checker

-- Índices de alto rendimiento para verificación de dependencias
-- Estos índices están optimizados para consultas EXISTS con LIMIT 1

-- Auto-referencias de animales (padre/madre) - las más críticas
CREATE INDEX ix_animals_idfather_exists ON animals(idFather);
CREATE INDEX ix_animals_idmother_exists ON animals(idMother);

-- Índices compuestos para verificación batch de animales
CREATE INDEX ix_animals_parent_check ON animals(idFather, idMother, id);

-- Dependencias directas (tablas hijas)
CREATE INDEX ix_treatments_animals_id_exists ON treatments(animals_id);
CREATE INDEX ix_vaccinations_animals_id_exists ON vaccinations(animals_id);
CREATE INDEX ix_animal_diseases_animal_id_exists ON animal_diseases(animal_id);
CREATE INDEX ix_control_animals_id_exists ON control(animals_id);
CREATE INDEX ix_animal_fields_animal_id_exists ON animal_fields(animal_id);
CREATE INDEX ix_genetic_improvements_animals_id_exists ON genetic_improvements(animals_id);

-- Índices para consultas batch (UNION ALL)
CREATE INDEX ix_animals_batch_delete_check ON animals(id, idFather, idMother, status);

-- Actualizar estadísticas del optimizador (MySQL)
ANALYZE TABLE animals;
ANALYZE TABLE treatments;
ANALYZE TABLE vaccinations;
ANALYZE TABLE animal_diseases;
ANALYZE TABLE control;
ANALYZE TABLE animal_fields;
ANALYZE TABLE genetic_improvements;

-- Notas de optimización para MySQL:
-- 1. Los índices simples son suficientes para EXISTS con LIMIT 1
-- 2. Los índices compuestos optimizan el orden de acceso para consultas batch
-- 3. EXISTS con LIMIT 1 se beneficia enormemente de estos índices
-- 4. El cache del integrity checker (TTL 30s) complementa estos índices
-- 5. MySQL no soporta INCLUDE como PostgreSQL, pero los índices simples son muy eficientes para EXISTS