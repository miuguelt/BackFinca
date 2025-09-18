"""
Script para migrar de enum RouteAdministration a tabla route_administrations
y actualizar la tabla medications
"""

import os
import sys

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Force remote DB URI
os.environ['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://fincau:fincac@isladigital.xyz:3311/finca'

from app import create_app, db
from sqlalchemy import text

app = create_app('development')

def migrate_route_administration():
    """Migrar de enum a tabla separada"""
    with app.app_context():
        try:
            print("=== INICIANDO MIGRACIÓN DE ROUTE_ADMINISTRATION ===")
            
            # 1. Crear la nueva tabla route_administrations
            print("1. Creando tabla route_administrations...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS route_administrations (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(50) NOT NULL UNIQUE,
                        description VARCHAR(255),
                        status BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    );
                """))
                conn.commit()
            
            # 2. Insertar las rutas de administración por defecto
            print("2. Insertando rutas de administración por defecto...")
            default_routes = [
                ('Oral', 'Administración por vía oral'),
                ('Inyección', 'Administración por inyección intramuscular o intravenosa'),
                ('Intranasal', 'Administración por vía nasal'),
                ('Tópica', 'Aplicación tópica sobre la piel o mucosas')
            ]
            
            with db.engine.connect() as conn:
                for name, description in default_routes:
                    try:
                        conn.execute(text("""
                            INSERT IGNORE INTO route_administrations (name, description, status)
                            VALUES (:name, :description, TRUE)
                        """), {"name": name, "description": description})
                    except Exception as e:
                        print(f"Error insertando {name}: {e}")
                conn.commit()
            
            # 3. Agregar nueva columna route_administration_id a medications
            print("3. Agregando columna route_administration_id a medications...")
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("""
                        ALTER TABLE medications 
                        ADD COLUMN route_administration_id INT
                    """))
                    conn.commit()
            except Exception as e:
                print(f"Columna ya existe o error: {e}")
            
            # 4. Migrar datos existentes
            print("4. Migrando datos existentes...")
            
            # Mapeo de enum values a IDs
            route_mapping = {
                'Oral': 1,
                'Inyección': 2, 
                'Intranasal': 3,
                'Tópica': 4
            }
            
            # Obtener medications existentes
            with db.engine.connect() as conn:
                try:
                    medications = conn.execute(text("SELECT id, route_administration FROM medications WHERE route_administration IS NOT NULL")).fetchall()
                    
                    for med in medications:
                        med_id, route_enum = med
                        if route_enum in route_mapping:
                            route_id = route_mapping[route_enum]
                            conn.execute(text("""
                                UPDATE medications 
                                SET route_administration_id = :route_id 
                                WHERE id = :med_id
                            """), {"route_id": route_id, "med_id": med_id})
                            print(f"Migrado medicamento {med_id}: {route_enum} -> {route_id}")
                    
                    conn.commit()
                except Exception as e:
                    print(f"Error migrando datos: {e}")
            
            # 5. Agregar foreign key constraint
            print("5. Agregando constraint de foreign key...")
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("""
                        ALTER TABLE medications 
                        ADD FOREIGN KEY (route_administration_id) REFERENCES route_administrations(id)
                    """))
                    conn.commit()
            except Exception as e:
                print(f"Error agregando foreign key: {e}")
            
            # 6. Eliminar la columna enum (opcional, puedes comentar esta sección si quieres mantener backup)
            print("6. Eliminando columna enum route_administration...")
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE medications DROP COLUMN route_administration"))
                    conn.commit()
            except Exception as e:
                print(f"Error eliminando columna enum: {e}")
            
            # 7. Hacer route_administration_id NOT NULL
            print("7. Configurando route_administration_id como NOT NULL...")
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("""
                        ALTER TABLE medications 
                        MODIFY COLUMN route_administration_id INT NOT NULL
                    """))
                    conn.commit()
            except Exception as e:
                print(f"Error configurando NOT NULL: {e}")
            
            print("=== MIGRACIÓN COMPLETADA EXITOSAMENTE ===")
            
        except Exception as e:
            print(f"Error durante la migración: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    migrate_route_administration()
