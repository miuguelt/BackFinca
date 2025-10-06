#!/usr/bin/env python3
"""
Script para probar las correcciones del verificador de integridad
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.animals import Animals
from app.utils.integrity_checker import OptimizedIntegrityChecker

def test_integrity_checker():
    """Prueba el verificador de integridad con las correcciones"""
    app = create_app()
    
    with app.app_context():
        print("🔍 Probando el verificador de integridad corregido...")
        
        # Obtener un animal de prueba
        animal = Animals.query.first()
        if not animal:
            print("❌ No se encontraron animales en la base de datos")
            return False
        
        print(f"📋 Probando con animal ID: {animal.id} - {animal.record}")
        
        # Limpiar cache para forzar verificación real
        OptimizedIntegrityChecker.clear_cache()
        
        try:
            # Probar verificación de integridad
            warnings = OptimizedIntegrityChecker.check_integrity_fast(Animals, animal.id)
            
            print(f"✅ Verificación completada sin errores")
            print(f"📊 Se encontraron {len(warnings)} advertencias de integridad:")
            
            for warning in warnings:
                print(f"   - Tabla: {warning.dependent_table}, Campo: {warning.dependent_field}, "
                      f"Count: {warning.dependent_count}, Cascade: {warning.cascade_delete}")
                print(f"     Mensaje: {warning.warning_message}")
            
            # Probar método can_delete_safely
            can_delete, delete_warnings = OptimizedIntegrityChecker.can_delete_safely(Animals, animal.id)
            print(f"🔒 ¿Se puede eliminar seguramente?: {'Sí' if can_delete else 'No'}")
            
            # Probar método get_deletion_summary
            summary = OptimizedIntegrityChecker.get_deletion_summary(Animals, animal.id)
            print(f"📋 Resumen de eliminación:")
            print(f"   - Dependencias totales: {summary['total_dependents']}")
            print(f"   - Eliminaciones en cascada: {summary['cascade_deletions']}")
            print(f"   - Dependencias bloqueantes: {summary['blocking_dependencies']}")
            print(f"   - Mensaje: {summary['summary_message']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error durante la verificación de integridad: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_relationships_detection():
    """Prueba la detección de relaciones"""
    app = create_app()
    
    with app.app_context():
        print("\n🔍 Probando detección de relaciones...")
        
        try:
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
            
            return True
            
        except Exception as e:
            print(f"❌ Error detectando relaciones: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("🚀 Iniciando pruebas del verificador de integridad corregido")
    print("=" * 60)
    
    success = True
    
    # Probar detección de relaciones
    if not test_relationships_detection():
        success = False
    
    # Probar verificación de integridad
    if not test_integrity_checker():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Todas las pruebas pasaron correctamente")
        print("✅ El verificador de integridad funciona correctamente con las correcciones")
    else:
        print("❌ Algunas pruebas fallaron")
        print("⚠️  Revisa los errores mostrados arriba")
    
    sys.exit(0 if success else 1)