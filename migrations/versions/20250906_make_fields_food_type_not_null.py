"""
Revision ID: 20250906_ft_not_null
Revises: 20250906_add_perf_indexes
Create Date: 2025-09-06

Make fields.food_type_id NOT NULL. This migration is intentionally conservative:
- It assumes data has been normalized (no NULLs) before running.
- For SQLite, manual table rebuild may be necessary; Alembic autogenerate on SQLite can't alter columns reliably.

Steps recommended before running:
1. Run scripts/migrate_fields_food_type_not_null.py to populate NULLs with a placeholder value.
2. Inspect and backup your DB.
3. Run alembic upgrade head.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250906_ft_not_null'
down_revision = '20250906_add_perf_indexes'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    dialect = conn.engine.name
    if dialect in ('postgresql', 'mysql', 'mariadb'):
        # Postgres/MySQL support altering column nullability directly
        if dialect == 'postgresql':
            op.execute('ALTER TABLE fields ALTER COLUMN food_type_id SET NOT NULL')
        else:
            op.execute('ALTER TABLE fields MODIFY COLUMN food_type_id INT NOT NULL')
    else:
        # SQLite path (SAFE): No alter para evitar recreación completa de tabla que podría causar pérdida de datos.
        # Se asume que la aplicación hará validación a nivel ORM y que un futuro hardening hará un rebuild planificado.
        print('[INFO] SQLite detectado: se omite ALTER TABLE para preservar datos. Validar que no existan NULLs y planificar rebuild futuro si se requiere constraint física.')


def downgrade():
    conn = op.get_bind()
    dialect = conn.engine.name
    if dialect in ('postgresql', 'mysql', 'mariadb'):
        if dialect == 'postgresql':
            op.execute('ALTER TABLE fields ALTER COLUMN food_type_id DROP NOT NULL')
        else:
            op.execute('ALTER TABLE fields MODIFY COLUMN food_type_id INT NULL')
    else:
        print('[INFO] SQLite: downgrade no-op (no constraint física aplicada).')
