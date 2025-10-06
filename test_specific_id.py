#!/usr/bin/env python3
"""
Script rápido para probar con un ID específico sin interacción.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_with_specific_id():
    """Prueba el integrity checker con un ID específico."""
    try:
        from app import create_app, db
        from app.models.animals import Animals
        from app.utils.integrity_checker import OptimizedIntegrityChecker
        from sqlalchemy import text
        
        app = create_app()
        
        with app.app_context():
            # Obtener el primer animal disponible
            animal = Animals.query.first()
            if not animal:
                print("No hay animales en la base de datos")
                return
            
            animal_id = animal.id
            print(f"Probando con animal ID: {animal_id} - {animal.record}")
            
            # Verificar dependencias reales con queries directas
            print("\nDependencias reales (queries directas):")
            
            # Hijos como padre
            query = text("SELECT COUNT(*) as count FROM animals WHERE idFather = :animal_id")
            result = db.session.execute(query, {'animal_id': animal_id}).fetchone()
            hijos_padre = result.count if result else 0
            print(f"  Hijos como padre: {hijos_padre}")
            
            # Hijos como madre
            query = text("SELECT COUNT(*) as count FROM animals WHERE idMother = :animal_id")
            result = db.session.execute(query, {'animal_id': animal_id}).fetchone()
            hijos_madre = result.count if result else 0
            print(f"  Hijos como madre: {hijos_madre}")
            
            # Tratamientos
            query = text("SELECT COUNT(*) as count FROM treatments WHERE animals_id = :animal_id")
            result = db.session.execute(query, {'animal_id': animal_id}).fetchone()
            treatments = result.count if result else 0
            print(f"  Tratamientos: {treatments}")
            
            # Vacunaciones
            query = text("SELECT COUNT(*) as count FROM vaccinations WHERE animals_id = :animal_id")
            result = db.session.execute(query, {'animal_id': animal_id}).fetchone()
            vaccinations = result.count if result else 0
            print(f"  Vacunaciones: {vaccinations}")
            
            # Ahora verificar con el integrity checker
            print("\nAdvertencias del Integrity Checker:")
            warnings = OptimizedIntegrityChecker.check_integrity_fast(Animals, animal_id)
            
            for warning in warnings:
                print(f"  Tabla: {warning.dependent_table}")
                print(f"    Count: {warning.dependent_count}")
                print(f"    Field: {warning.dependent_field}")
                print(f"    Cascade: {warning.cascade_delete}")
                print(f"    Message: {warning.warning_message}")
            
            # Comparar resultados
            print(f"\nCOMPARACIÓN:")
            print(f"  Método directo - Hijos padre: {hijos_padre}")
            print(f"  Método directo - Hijos madre: {hijos_madre}")
            print(f"  Método directo - Tratamientos: {treatments}")
            print(f"  Método directo - Vacunaciones: {vaccinations}")
            print(f"  Integrity Checker - Advertencias: {len(warnings)}")
            
            # Buscar discrepancias
            discrepancies = []
            for warning in warnings:
                if warning.dependent_table == 'animals':
                    if warning.dependent_field == 'idFather':
                        if warning.dependent_count != hijos_padre:
                            discrepancies.append(f"idFather: IC={warning.dependent_count} vs Real={hijos_padre}")
                    elif warning.dependent_field == 'idMother':
                        if warning.dependent_count != hijos_madre:
                            discrepancies.append(f"idMother: IC={warning.dependent_count} vs Real={hijos_madre}")
                elif warning.dependent_table == 'treatments':
                    if warning.dependent_count != treatments:
                        discrepancies.append(f"treatments: IC={warning.dependent_count} vs Real={treatments}")
                elif warning.dependent_table == 'vaccinations':
                    if warning.dependent_count != vaccinations:
                        discrepancies.append(f"vaccinations: IC={warning.dependent_count} vs Real={vaccinations}")
            
            if discrepancies:
                print(f"\n⚠️  DISCREPANCIAS ENCONTRADAS:")
                for disc in discrepancies:
                    print(f"  - {disc}")
            else:
                print(f"\n✅ NO HAY DISCREPANCIAS - Resultados coinciden")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_specific_id()