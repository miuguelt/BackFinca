"""
Script de prueba para el verificador de integridad referencial optimizado
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.integrity_checker import OptimizedIntegrityChecker, check_before_delete
from app.models.animals import Animals
from app.models.breeds import Breeds
from app.models.species import Species
from app import db
import time

def test_integrity_checker():
    """Prueba el verificador de integridad con diferentes escenarios"""
    
    print("=== Prueba del Verificador de Integridad Referencial ===\n")
    
    # Probar con un animal que probablemente no existe
    print("1. Probando con ID inexistente (debe ser rápido)...")
    start_time = time.time()
    warnings = OptimizedIntegrityChecker.check_integrity_fast(Animals, 999999)
    elapsed = time.time() - start_time
    print(f"   Tiempo: {elapsed:.3f}s")
    print(f"   Advertencias: {len(warnings)}")
    
    # Probar con una raza que probablemente no existe
    print("\n2. Probando con raza inexistente...")
    start_time = time.time()
    warnings = OptimizedIntegrityChecker.check_integrity_fast(Breeds, 999999)
    elapsed = time.time() - start_time
    print(f"   Tiempo: {elapsed:.3f}s")
    print(f"   Advertencias: {len(warnings)}")
    
    # Probar con especie que probablemente no existe
    print("\n3. Probando con especie inexistente...")
    start_time = time.time()
    warnings = OptimizedIntegrityChecker.check_integrity_fast(Species, 999999)
    elapsed = time.time() - start_time
    print(f"   Tiempo: {elapsed:.3f}s")
    print(f"   Advertencias: {len(warnings)}")
    
    # Probar cache (segunda llamada al mismo ID)
    print("\n4. Probando cache (segunda llamada mismo ID)...")
    start_time = time.time()
    warnings = OptimizedIntegrityChecker.check_integrity_fast(Animals, 999999)
    elapsed = time.time() - start_time
    print(f"   Tiempo: {elapsed:.3f}s (debe ser más rápido por cache)")
    print(f"   Advertencias: {len(warnings)}")
    
    # Probar función de conveniencia
    print("\n5. Probando función de conveniencia check_before_delete...")
    start_time = time.time()
    summary = check_before_delete(Animals, 999999)
    elapsed = time.time() - start_time
    print(f"   Tiempo: {elapsed:.3f}s")
    print(f"   Puede eliminar: {summary['can_delete']}")
    print(f"   Total dependientes: {summary['total_dependents']}")
    print(f"   Mensaje: {summary['summary_message']}")
    
    # Si hay animales en la BD, probar con el primero
    print("\n6. Probando con animal real (si existe)...")
    first_animal = Animals.query.first()
    if first_animal:
        print(f"   Animal ID: {first_animal.id}, Record: {first_animal.record}")
        start_time = time.time()
        summary = check_before_delete(Animals, first_animal.id)
        elapsed = time.time() - start_time
        print(f"   Tiempo: {elapsed:.3f}s")
        print(f"   Puede eliminar: {summary['can_delete']}")
        print(f"   Total dependientes: {summary['total_dependents']}")
        print(f"   Eliminaciones cascade: {summary['cascade_deletions']}")
        print(f"   Dependencias bloqueantes: {summary['blocking_dependencies']}")
        
        if summary['warnings']:
            print("   Advertencias detalladas:")
            for warning in summary['warnings']:
                print(f"     - {warning['message']}")
    else:
        print("   No hay animales en la BD para probar")
    
    print("\n=== Prueba completada ===")

def test_performance():
    """Prueba de rendimiento con múltiples llamadas"""
    print("\n=== Prueba de Rendimiento ===")
    
    # Probar múltiples llamadas para medir rendimiento
    test_ids = [999999, 888888, 777777, 666666, 555555]
    
    print("Primeras llamadas (sin cache)...")
    start_time = time.time()
    for animal_id in test_ids:
        warnings = OptimizedIntegrityChecker.check_integrity_fast(Animals, animal_id)
    first_round_time = time.time() - start_time
    print(f"Tiempo total primeras 5 llamadas: {first_round_time:.3f}s")
    print(f"Promedio por llamada: {first_round_time/5:.3f}s")
    
    print("\nSegundas llamadas (con cache)...")
    start_time = time.time()
    for animal_id in test_ids:
        warnings = OptimizedIntegrityChecker.check_integrity_fast(Animals, animal_id)
    second_round_time = time.time() - start_time
    print(f"Tiempo total segundas 5 llamadas: {second_round_time:.3f}s")
    print(f"Promedio por llamada: {second_round_time/5:.3f}s")
    print(f"Mejora con cache: {((first_round_time - second_round_time) / first_round_time * 100):.1f}%")

if __name__ == "__main__":
    try:
        test_integrity_checker()
        test_performance()
    except Exception as e:
        print(f"Error en prueba: {e}")
        import traceback
        traceback.print_exc()