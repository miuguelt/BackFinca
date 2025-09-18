Alembic Migrations
==================

Comandos básicos:

Crear nueva migración autogenerada (describir cambios):
  alembic revision --autogenerate -m "descripcion"

Aplicar migraciones:
  alembic upgrade head

Revertir última migración:
  alembic downgrade -1

Ver historial:
  alembic history --verbose

Sincronizar DB existente tras añadir Alembic:
  1. Generar migración vacía inicial y marcar estado actual:
     alembic revision -m "baseline" --autogenerate
  2. Revisar que no intenta recrear tablas (editar si es necesario)
  3. upgrade head

Índices añadidos en esta fase (asegurar migración los incluye si no existen ya):
  animals: (breeds_id,status), (created_at)
  control: (animal_id,checkup_date), (created_at)
  treatments: (animal_id,treatment_date), (created_at)
  vaccinations: (animal_id,vaccination_date), (created_at)
