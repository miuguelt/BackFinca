"""
add performance indexes

Revision ID: 20250906_add_perf_indexes
Revises: 
Create Date: 2025-09-06
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250906_add_perf_indexes'
down_revision = None
branch_labels = None
depends_on = None

# Helpers to avoid duplicate index errors when the index already exists in DB

def _index_exists(conn, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(conn)
    try:
        indexes = inspector.get_indexes(table_name)
    except Exception:
        return False
    return any(ix.get('name') == index_name for ix in indexes)


def _create_index_if_not_exists(index_name: str, table_name: str, columns, unique: bool = False):
    conn = op.get_bind()
    if not _index_exists(conn, table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def upgrade():
    # animals
    _create_index_if_not_exists('ix_animals_breeds_status', 'animals', ['breeds_id', 'status'], unique=False)
    _create_index_if_not_exists('ix_animals_created_at', 'animals', ['created_at'], unique=False)
    # control
    _create_index_if_not_exists('ix_control_animal_checkup', 'control', ['animal_id', 'checkup_date'], unique=False)
    _create_index_if_not_exists('ix_control_created_at', 'control', ['created_at'], unique=False)
    # treatments
    _create_index_if_not_exists('ix_treatments_animal_date', 'treatments', ['animal_id', 'treatment_date'], unique=False)
    _create_index_if_not_exists('ix_treatments_created_at', 'treatments', ['created_at'], unique=False)
    # vaccinations
    _create_index_if_not_exists('ix_vaccinations_animal_date', 'vaccinations', ['animal_id', 'vaccination_date'], unique=False)
    _create_index_if_not_exists('ix_vaccinations_created_at', 'vaccinations', ['created_at'], unique=False)


def downgrade():
    # vaccinations
    op.drop_index('ix_vaccinations_created_at', table_name='vaccinations')
    op.drop_index('ix_vaccinations_animal_date', table_name='vaccinations')
    # treatments
    op.drop_index('ix_treatments_created_at', table_name='treatments')
    op.drop_index('ix_treatments_animal_date', table_name='treatments')
    # control
    op.drop_index('ix_control_created_at', table_name='control')
    op.drop_index('ix_control_animal_checkup', table_name='control')
    # animals
    op.drop_index('ix_animals_created_at', table_name='animals')
    op.drop_index('ix_animals_breeds_status', table_name='animals')
