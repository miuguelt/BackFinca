#!/usr/bin/env python3
"""
Script de prueba para validar las optimizaciones del Integrity Checker.

Este script mide el rendimiento de las consultas de integridad referencial
antes y después de las optimizaciones implementadas.
"""

import time
import sys
import os
from typing import Dict, List
import statistics

# Agregar el directorio raíz al path para importar la app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.animals import Animals
from app.models.breeds import Breeds
from app.models.species import Species
from app.models.treatments import Treatments
from app.models.vaccinations import Vaccinations
from app.utils.integrity_checker import OptimizedIntegrityChecker

def setup_test_data():
    """Crea datos de prueba para las mediciones de rendimiento."""
    print("Creando datos de prueba...")
    
    # Crear especie
    species = Species(name="Bovino Test")
    db.session.add(species)
    db.session.flush()
    
    # Crear raza
    breed = Breeds(name="Holando Test", species_id=species.id)
    db.session.add(breed)
    db.session.flush()
    
    # Crear animales con dependencias
    test_animals = []
    for i in range(10):
        animal = Animals(
            record=f"TEST-{i:03d}",
            sex="Macho",
            birth_date="2020-01-01",
            weight=500,
            breeds_id=breed.id
        )
        db.session.add(animal)
        test_animals.append(animal)
    
    db.session.flush()
    
    # Crear tratamientos para algunos animales (campos obligatorios completos)
    for i, animal in enumerate(test_animals[:5]):
        treatment = Treatments(
            animal_id=animal.id,
            treatment_date="2023-01-01",
            description=f"Tratamiento test {i}",
            frequency="Diaria",
            dosis="10mg"
        )
        db.session.add(treatment)
    
    db.session.commit()
    print(f"Creados {len(test_animals)} animales con dependencias")
    
    return test_animals

def measure_performance(test_animals: List[Animals], iterations: int = 5) -> Dict:
    """Mide el rendimiento de las consultas de integridad."""
    results = {
        'individual_checks': [],
        'batch_checks': [],
        'cache_performance': []
    }
    
    print(f"\nEjecutando {iterations} iteraciones de pruebas de rendimiento...")
    
    for iteration in range(iterations):
        print(f"Iteración {iteration + 1}/{iterations}")
        
        # Limpiar cache para medición justa
        OptimizedIntegrityChecker.clear_cache()
        
        # 1. Medir checks individuales
        start_time = time.time()
        for animal in test_animals:
            warnings = OptimizedIntegrityChecker.check_integrity_fast(Animals, animal.id)
        individual_time = time.time() - start_time
        results['individual_checks'].append(individual_time)
        
        # 2. Medir checks con cache (segunda pasada)
        start_time = time.time()
        for animal in test_animals:
            warnings = OptimizedIntegrityChecker.check_integrity_fast(Animals, animal.id)
        cache_time = time.time() - start_time
        results['cache_performance'].append(cache_time)
        
        # 3. Obtener estadísticas del cache
        cache_stats = OptimizedIntegrityChecker.get_cache_stats()
        print(f"  - Cache stats: {cache_stats['valid_entries']} entradas válidas")
    
    return results

def analyze_results(results: Dict) -> None:
    """Analiza y muestra los resultados de rendimiento."""
    print("\n" + "="*60)
    print("ANÁLISIS DE RENDIMIENTO - INTEGRITY CHECKER OPTIMIZADO")
    print("="*60)
    
    # Análisis de checks individuales
    individual_times = results['individual_checks']
    cache_times = results['cache_performance']
    
    print(f"\n1. CHECKS INDIVIDUALES (sin cache):")
    print(f"   - Tiempo promedio: {statistics.mean(individual_times):.4f}s")
    print(f"   - Tiempo mínimo: {min(individual_times):.4f}s")
    print(f"   - Tiempo máximo: {max(individual_times):.4f}s")
    print(f"   - Desviación estándar: {statistics.stdev(individual_times):.4f}s")
    
    print(f"\n2. CHECKS CON CACHE:")
    print(f"   - Tiempo promedio: {statistics.mean(cache_times):.4f}s")
    print(f"   - Tiempo mínimo: {min(cache_times):.4f}s")
    print(f"   - Tiempo máximo: {max(cache_times):.4f}s")
    print(f"   - Desviación estándar: {statistics.stdev(cache_times):.4f}s")
    
    # Calcular mejoras
    avg_individual = statistics.mean(individual_times)
    avg_cache = statistics.mean(cache_times)
    improvement = ((avg_individual - avg_cache) / avg_individual) * 100
    
    print(f"\n3. MEJORAS DE RENDIMIENTO:")
    print(f"   - Mejora promedio con cache: {improvement:.1f}%")
    print(f"   - Factor de velocidad: {avg_individual / avg_cache:.1f}x más rápido")
    
    # Estadísticas finales del cache
    final_cache_stats = OptimizedIntegrityChecker.get_cache_stats()
    print(f"\n4. ESTADÍSTICAS FINALES DEL CACHE:")
    print(f"   - Entradas totales: {final_cache_stats['total_entries']}")
    print(f"   - Entradas válidas: {final_cache_stats['valid_entries']}")
    print(f"   - Uso de memoria estimado: {final_cache_stats['memory_usage_estimate']} bytes")

def test_integrity_accuracy(test_animals: List[Animals]) -> None:
    """Verifica la precisión de las advertencias de integridad."""
    print("\n" + "="*60)
    print("PRUEBA DE PRECISIÓN - ADVERTENCIAS DE INTEGRIDAD")
    print("="*60)
    
    # Probar un animal con dependencias conocidas
    test_animal = test_animals[0]  # Primer animal tiene tratamiento
    
    print(f"\nVerificando animal: {test_animal.record} (ID: {test_animal.id})")
    
    # Obtener advertencias de integridad
    warnings = OptimizedIntegrityChecker.check_integrity_fast(Animals, test_animal.id)
    
    print(f"\nAdvertencias encontradas: {len(warnings)}")
    for warning in warnings:
        print(f"  - Tabla: {warning.dependent_table}")
        print(f"    Count: {warning.dependent_count}")
        print(f"    Field: {warning.dependent_field}")
        print(f"    Cascade: {warning.cascade_delete}")
        print(f"    Message: {warning.warning_message}")
        print()
    
    # Verificar si puede eliminarse
    can_delete, delete_warnings = OptimizedIntegrityChecker.can_delete_safely(Animals, test_animal.id)
    print(f"¿Puede eliminarse seguramente? {'SÍ' if can_delete else 'NO'}")
    
    # Obtener resumen completo
    summary = OptimizedIntegrityChecker.get_deletion_summary(Animals, test_animal.id)
    print(f"\nResumen de eliminación:")
    print(f"  - Total dependientes: {summary['total_dependents']}")
    print(f"  - Eliminaciones en cascade: {summary['cascade_deletions']}")
    print(f"  - Dependencias bloqueantes: {summary['blocking_dependencies']}")
    print(f"  - Mensaje: {summary['summary_message']}")

def cleanup_test_data(test_animals: List[Animals]) -> None:
    """Limpia los datos de prueba."""
    print("\nLimpiando datos de prueba...")
    
    try:
        # Eliminar en orden inverso para evitar FK constraints
        for animal in test_animals:
            # Las dependencias se eliminarán en cascade si están configuradas
            db.session.delete(animal)
        
        db.session.commit()
        print("Datos de prueba eliminados correctamente")
    except Exception as e:
        print(f"Error limpiando datos: {e}")
        db.session.rollback()

def main():
    """Función principal del script de pruebas."""
    app = create_app()
    
    with app.app_context():
        print("INICIANDO PRUEBAS DE RENDIMIENTO - INTEGRITY CHECKER")
        print("="*60)
        
        try:
            # Crear datos de prueba
            test_animals = setup_test_data()
            
            # Probar precisión de las advertencias
            test_integrity_accuracy(test_animals)
            
            # Medir rendimiento
            results = measure_performance(test_animals)
            
            # Analizar resultados
            analyze_results(results)
            
            # Limpiar datos
            cleanup_test_data(test_animals)
            
            print("\n" + "="*60)
            print("PRUEBAS COMPLETADAS EXITOSAMENTE")
            print("="*60)
            
        except Exception as e:
            print(f"\nERROR durante las pruebas: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
