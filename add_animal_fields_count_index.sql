-- ====================================================================
-- Migración: Agregar índice compuesto en animal_fields para optimizar conteo
-- Fecha: 2025-10-15
-- Descripción: Mejora el rendimiento del conteo de animales por campo
--              Optimiza la query que cuenta animales activos (removal_date IS NULL)
-- ====================================================================

-- Índice compuesto para optimizar el conteo de animales por campo
-- Este índice acelera las queries que filtran por field_id y removal_date IS NULL
CREATE INDEX idx_animal_fields_field_removal ON animal_fields(field_id, removal_date);

-- Verificación
SELECT 'Index idx_animal_fields_field_removal created successfully!' AS STATUS;
