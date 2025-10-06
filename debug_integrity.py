#!/usr/bin/env python3
"""
Script de depuración para investigar falsos positivos en integridad referencial.
"""

import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_integrity_checker():
    """Depura el integrity checker para encontrar el problema."""
    print("DEPURACIÓN - INTEGRITY CHECKER")
    print("="*50)
    
    # Importar después de configurar el path
    try:
        from app.models.animals import Animals
        from app.utils.integrity_checker import OptimizedIntegrityChecker
        
        print("Modelos importados correctamente")
        
        # Analizar las relaciones del modelo Animals
        print("\n1. ANALIZANDO RELACIONES DEL MODELO ANIMALS:")
        print("-" * 40)
        
        relationships = OptimizedIntegrityChecker._get_model_relationships(Animals)
        
        for i, rel in enumerate(relationships):
            print(f"\nRelación {i+1}:")
            print(f"  name: {rel['name']}")
            print(f"  target_table: {rel['target_table']}")
            print(f"  foreign_keys: {rel['foreign_keys']}")
            print(f"  cascade: {rel['cascade']}")
            print(f"  collection: {rel['collection']}")
            print(f"  reverse: {rel.get('reverse', False)}")
        
        print(f"\nTotal de relaciones detectadas: {len(relationships)}")
        
        # Verificar específicamente las relaciones de padre/madre
        print("\n2. VERIFICANDO RELACIONES PADRE/MADRE:")
        print("-" * 40)
        
        # Analizar las columnas de la tabla animals
        print("Columnas de la tabla animals:")
        for column in Animals.__table__.columns:
            print(f"  {column.name}: {column.type}")
            if column.foreign_keys:
                for fk in column.foreign_keys:
                    print(f"    -> FK: {fk.column}")
        
        # Revisar las relaciones SQLAlchemy
        print("\nRelaciones SQLAlchemy:")
        mapper = Animals.__mapper__
        for rel in mapper.relationships:
            print(f"  {rel.key}:")
            print(f"    target: {rel.mapper.class_.__name__}")
            print(f"    local_columns: {[str(col) for col in rel.local_columns]}")
            try:
                print(f"    foreign_keys: {[str(fk) for fk in rel.foreign_keys]}")
            except AttributeError:
                print(f"    foreign_keys: [No disponible]")
            print(f"    cascade: {rel.cascade}")
            print(f"    uselist: {rel.uselist}")
        
        return True
        
    except Exception as e:
        print(f"Error durante la depuración: {e}")
        import traceback
        traceback.print_exc()
        return False

def debug_specific_animal(animal_id=None):
    """Depura un animal específico para ver las dependencias reales."""
    if not animal_id:
        print("\n3. DEPURACIÓN DE ANIMAL ESPECÍFICO:")
        print("-" * 40)
        print("Por favor, proporciona un ID de animal para depurar:")
        animal_id = input("ID del animal: ").strip()
        
        if not animal_id.isdigit():
            print("ID inválido")
            return
    
    try:
        from app import create_app, db
        from app.models.animals import Animals
        from app.utils.integrity_checker import OptimizedIntegrityChecker
        from sqlalchemy import text
        
        app = create_app()
        
        with app.app_context():
            print(f"\nDepurando animal ID: {animal_id}")
            
            # Verificar si el animal existe
            animal = Animals.query.filter_by(id=animal_id).first()
            if not animal:
                print(f"El animal con ID {animal_id} no existe")
                return
            
            print(f"Animal encontrado: {animal.record}")
            
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
            warnings = OptimizedIntegrityChecker.check_integrity_fast(Animals, int(animal_id))
            
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
            print(f"  Integrity Checker - Advertencias: {len(warnings)}")
            
            # Buscar discrepancias
            for warning in warnings:
                if warning.dependent_table == 'animals':
                    if warning.dependent_field == 'idFather':
                        if warning.dependent_count != hijos_padre:
                            print(f"  ⚠️  DISCREPANCIA: idFather {warning.dependent_count} vs {hijos_padre}")
                    elif warning.dependent_field == 'idMother':
                        if warning.dependent_count != hijos_madre:
                            print(f"  ⚠️  DISCREPANCIA: idMother {warning.dependent_count} vs {hijos_madre}")
    
    except Exception as e:
        print(f"Error depurando animal específico: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Función principal."""
    print("DEPURADOR DE INTEGRIDAD REFERENCIAL")
    print("="*60)
    
    # Primero analizar el modelo
    if debug_integrity_checker():
        # Luego depurar un animal específico si se desea
        debug_specific_animal()
    
    print("\n" + "="*60)
    print("DEPURACIÓN COMPLETADA")

if __name__ == "__main__":
    main()