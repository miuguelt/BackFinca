import logging
from typing import Optional


def seed_admin_user(app, logger: Optional[logging.Logger] = None) -> None:
    """
    Crea un usuario administrador semilla si la tabla y el usuario no existen.
    Pensado para ejecutarse durante el arranque de la app (create_app).

    - identification: 99999999
    - fullname: "Admin Seed"
    - email: "admin.seed@example.com"
    - phone: "3000000000"
    - password: "password123" (hashed)
    - role: Role.Administrador
    """
    _logger = logger or logging.getLogger(__name__)

    try:
        # Importaciones diferidas para evitar ciclos de importación durante el arranque
        from app import db  # type: ignore
        from app.models.user import User, Role  # type: ignore
        from sqlalchemy import inspect as sqlalchemy_inspect, or_  # type: ignore
        from werkzeug.security import generate_password_hash  # type: ignore

        with app.app_context():
            try:
                inspector = sqlalchemy_inspect(db.engine)
                if 'user' not in inspector.get_table_names():
                    _logger.info('Skipping seed admin: tabla user no existe aún')
                    return

                # Evitar errores por restricciones UNIQUE
                existing = User.query.filter(
                    or_(
                        User.identification == 99999999,
                        User.email == 'admin.seed@example.com',
                        User.phone == '3000000000',
                    )
                ).first()

                if existing:
                    _logger.info(
                        'Usuario administrador semilla existente (id=%s ident=%s)',
                        getattr(existing, 'id', None),
                        getattr(existing, 'identification', None),
                    )
                    return

                seed_admin = User(
                    identification=99999999,
                    fullname='Admin Seed',
                    password=generate_password_hash('password123'),
                    email='admin.seed@example.com',
                    phone='3000000000',
                    address='Main HQ',
                    role=Role.Administrador,
                    status=True,
                )
                db.session.add(seed_admin)
                db.session.commit()
                _logger.info('Usuario administrador semilla creado (identification=99999999)')
            except Exception as e:
                db.session.rollback()
                _logger.warning('Error verificando/creando usuario semilla: %s', e, exc_info=True)
    except Exception as e:
        _logger.warning('No se pudo crear usuario administrador semilla: %s', e, exc_info=True)