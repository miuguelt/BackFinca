"""
normalize fields.food_type_id data (non-destructive)

Revision ID: 20250906_norm_food_type
Revises: 20250906_ft_not_null
Create Date: 2025-09-06

Objetivo: asegurar que no existan filas con food_type_id NULL asignando un placeholder.
No aplica ALTER TABLE en SQLite (evita reconstrucción que pueda truncar datos).
"""
from alembic import op
import sqlalchemy as sa

revision = '20250906_norm_food_type'
down_revision = '20250906_ft_not_null'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    dialect = conn.engine.name
    # Crear placeholder si no existe
    result = conn.execute(sa.text("SELECT id FROM food_types WHERE food_type='Sin especificar'"))
    row = result.fetchone()
    if row:
        placeholder_id = row[0]
    else:
        # Insertar con valores por defecto seguros para posibles columnas NOT NULL
        ins = conn.execute(
            sa.text(
                """
                INSERT INTO food_types (
                    food_type, handlings, gauges, sowing_date, harvest_date, area, created_at, updated_at
                ) VALUES (
                    :ft, :h, :g, :sd, :hd, :ar, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "ft": "Sin especificar",
                "h": "Placeholder autogenerado",
                "g": "Placeholder",
                "sd": "1970-01-01",
                "hd": "1970-01-01",
                "ar": 0,
            },
        )
        placeholder_id = ins.lastrowid if hasattr(ins, 'lastrowid') else conn.execute(sa.text("SELECT id FROM food_types WHERE food_type='Sin especificar'")) .fetchone()[0]

    # Actualizar filas NULL
    updated = conn.execute(sa.text("UPDATE fields SET food_type_id = :pid WHERE food_type_id IS NULL"), {"pid": placeholder_id})
    try:
        count_attr = updated.rowcount
    except Exception:
        count_attr = 'desconocido'
    print(f"[INFO] Normalización fields.food_type_id -> placeholder {placeholder_id}. Filas actualizadas: {count_attr}")

    # Solo en Postgres/MySQL aplicar constraint si no está ya
    if dialect in ('postgresql', 'mysql', 'mariadb'):
        try:
            if dialect == 'postgresql':
                conn.execute(sa.text('ALTER TABLE fields ALTER COLUMN food_type_id SET NOT NULL'))
            else:
                conn.execute(sa.text('ALTER TABLE fields MODIFY COLUMN food_type_id INT NOT NULL'))
            print('[INFO] Constraint NOT NULL aplicada exitosamente.')
        except Exception as ex:
            print('[WARN] No se pudo aplicar constraint NOT NULL automáticamente:', ex)
    else:
        print('[INFO] SQLite: se omite ALTER TABLE (no destructivo).')


def downgrade():
    conn = op.get_bind()
    dialect = conn.engine.name
    if dialect in ('postgresql', 'mysql', 'mariadb'):
        try:
            if dialect == 'postgresql':
                conn.execute(sa.text('ALTER TABLE fields ALTER COLUMN food_type_id DROP NOT NULL'))
            else:
                conn.execute(sa.text('ALTER TABLE fields MODIFY COLUMN food_type_id INT NULL'))
            print('[INFO] Constraint NOT NULL revertida.')
        except Exception as ex:
            print('[WARN] No se pudo revertir constraint NOT NULL:', ex)
    else:
        print('[INFO] SQLite: downgrade no-op.')
