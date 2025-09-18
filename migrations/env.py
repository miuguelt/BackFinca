import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Interpret the config file for Python logging.
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add application model metadata
from app import create_app, db  # type: ignore

app = create_app()
with app.app_context():
    target_metadata = db.metadata

    def run_migrations_offline():
        url = os.getenv('SQLALCHEMY_DATABASE_URI')
        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
        with context.begin_transaction():
            context.run_migrations()

    def run_migrations_online():
        configuration = config.get_section(config.config_ini_section)
        if 'sqlalchemy.url' not in configuration or not configuration['sqlalchemy.url']:
            configuration['sqlalchemy.url'] = os.getenv('SQLALCHEMY_DATABASE_URI')
        connectable = engine_from_config(
            configuration,
            prefix='sqlalchemy.',
            poolclass=pool.NullPool,
        )
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()

    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
