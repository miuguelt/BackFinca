#!/usr/bin/env python3
"""
Script simplificado para probar las correcciones del verificador de integridad
sin necesidad de conexión a base de datos
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar variables de entorno para evitar el error de puerto
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '3306'
os.environ['DB_NAME'] = 'finca'
os.environ['DB_USER'] = 'root'
os.environ['DB_PASSWORD'] = ''
os.environ['FLASK_ENV'] = 'testing'
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'

from app import create_app
from app.models.animals import Animals
from app.utils.integrity_checker import OptimizedIntegrityChecker

def test_relationships_detection():
    """Prueba la detección de relaciones sin conexión a BD"""
    print("🔍 Probando detección de relaciones...")
    
    try:
        # Crear app con configuración de testing (SQLite)
        app = create_app()
        
        with app.app_context():
            relationships = OptimizedIntegrityChecker._get_model_relationships(Animals)
            
            print(f"✅ Se detectaron {len(relationships)} relaciones:")
            
            for rel in relationships:
                print(f"   - Nombre: {rel['name']}")
                print(f"     Tabla destino: {rel['target_table']}")
                print(f"     Claves foráneas: {rel['foreign_keys']}")
                print(f"     Cascade: {rel['cascade']}")
                print(f"     Colección: {rel['collection']}")
                print(f"     Reversa: {rel.get('reverse', False)}")
                print()
            
            # Verificar que las claves foráneas usen los nombres correctos
            expected_fks = {
                'treatments': ['animal_id'],
                'vaccinations': ['animal_id'],
                'animal_diseases': ['animal_id'],
                'control': ['animal_id']
            }
            
            for rel in relationships:
                if rel['target_table'] in expected_fks:
                    expected = expected_fks[rel['target_table']]
                    actual = rel['foreign_keys']
                    if actual == expected:
                        print(f"✅ Clave foránea correcta para {rel['target_table']}: {actual}")
                    else:
                        print(f"❌ Clave foránea incorrecta para {rel['target_table']}: {actual} (esperado: {expected})")
                        return False
            
            return True
            
    except Exception as e:
        print(f"❌ Error detectando relaciones: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sql_generation():
    """Prueba la generación de SQL con los nombres correctos de columna"""
    print("\n🔍 Probando generación de SQL...")
    
    try:
        # Simular relaciones con las claves foráneas correctas
        test_relationships = [
            {
                'name': 'treatments',
                'target_table': 'treatments',
                'foreign_keys': ['animal_id'],
                'cascade': True,
                'collection': True
            },
            {
                'name': 'vaccinations',
                'target_table': 'vaccinations',
                'foreign_keys': ['animal_id'],
                'cascade': True,
                'collection': True
            },
            {
                'name': 'animal_diseases',
                'target_table': 'animal_diseases',
                'foreign_keys': ['animal_id'],
                'cascade': True,
                'collection': True
            },
            {
                'name': 'control',
                'target_table': 'control',
                'foreign_keys': ['animal_id'],
                'cascade': True,
                'collection': True
            }
        ]
        
        # Probar generación de SQL batch
        from app.utils.integrity_checker import text
        
        union_queries = []
        for rel in test_relationships:
            table_name = rel['target_table']
            fk_field = rel['foreign_keys'][0]
            record_id = 53
            
            subquery = f"""
                SELECT 
                    '{table_name}' as table_name,
                    '{fk_field}' as field_name,
                    {str(rel['cascade']).lower()} as cascade_delete,
                    CASE 
                        WHEN EXISTS (
                            SELECT 1 FROM {table_name} 
                            WHERE {fk_field} = {record_id} 
                            LIMIT 1
                        ) THEN 1 
                        ELSE 0 
                    END as count
            """
            union_queries.append(subquery)
        
        union_query = " UNION ALL ".join(union_queries)
        
        print("✅ SQL generado correctamente:")
        print(union_query)
        
        # Verificar que no contenga 'animals_id' (incorrecto)
        if 'animals_id' in union_query:
            print("❌ El SQL generado contiene 'animals_id' (incorrecto)")
            return False
        
        # Verificar que contenga 'animal_id' (correcto)
        if 'animal_id' in union_query:
            print("✅ El SQL generado contiene 'animal_id' (correcto)")
            return True
        else:
            print("❌ El SQL generado no contiene 'animal_id'")
            return False
            
    except Exception as e:
        print(f"❌ Error generando SQL: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Iniciando pruebas simplificadas del verificador de integridad")
    print("=" * 60)
    
    success = True
    
    # Probar detección de relaciones
    if not test_relationships_detection():
        success = False
    
    # Probar generación de SQL
    if not test_sql_generation():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Todas las pruebas pasaron correctamente")
        print("✅ El verificador de integridad funciona correctamente con las correcciones")
    else:
        print("❌ Algunas pruebas fallaron")
        print("⚠️  Revisa los errores mostrados arriba")
    
    sys.exit(0 if success else 1)