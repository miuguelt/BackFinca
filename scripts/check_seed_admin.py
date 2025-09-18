#!/usr/bin/env python3
"""
Script para verificar el estado del usuario administrador semilla
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force testing config to use a file-based SQLite DB so the running server and this
# script operate on the same persistent DB during tests.
os.environ['FLASK_ENV'] = os.environ.get('FLASK_ENV', 'testing')
os.environ['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///finca_test.db')

from app import create_app, db
from app.models.user import User, Role

def check_seed_admin():
    app = create_app('testing')

    with app.app_context():
        try:
            # Ensure tables exist so queries don't attempt to reach external DBs
            db.create_all()

            # Verificar si existe el usuario semilla
            seed_user = User.query.filter_by(identification=1098).first()

            if seed_user:
                print("✅ Usuario administrador semilla encontrado:")
                print(f"   ID: {seed_user.id}")
                print(f"   Identificación: {seed_user.identification}")
                print(f"   Nombre: {seed_user.fullname}")
                print(f"   Email: {seed_user.email}")
                print(f"   Rol: {seed_user.role}")
                print(f"   Estado: {seed_user.status}")
                print(f"   Contraseña hasheada: {seed_user.password[:20]}...")

                # Verificar contraseña
                from werkzeug.security import check_password_hash
                is_valid = check_password_hash(seed_user.password, 'password123')
                print(f"   Contraseña 'password123' válida: {is_valid}")

            else:
                print("❌ Usuario administrador semilla NO encontrado")
                print("Intentando crear usuario semilla...")

                from werkzeug.security import generate_password_hash

                seed_admin = User(
                    identification=99999999,
                    fullname='Admin Seed',
                    password=generate_password_hash('password123'),
                    email='admin.seed@example.com',
                    phone='3000000000',
                    address='Main HQ',
                    role=Role.Administrador,
                    status=True
                )

                db.session.add(seed_admin)
                db.session.commit()
                print("✅ Usuario administrador semilla creado exitosamente")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    check_seed_admin()
