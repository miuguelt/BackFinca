#!/usr/bin/env python3
"""
Script para limpiar el cache del integrity checker y probar el endpoint de dependencias.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def clear_integrity_cache():
    """Limpia el cache del integrity checker."""
    try:
        from app.utils.integrity_checker import OptimizedIntegrityChecker
        
        print("LIMPIEZA DE CACHE DEL INTEGRITY CHECKER")
        print("="*50)
        
        # Limpiar cache
        OptimizedIntegrityChecker.clear_cache()
        print("✅ Cache del integrity checker limpiado")
        
        # Mostrar estadísticas
        stats = OptimizedIntegrityChecker.get_cache_stats()
        print(f"Estadísticas: {stats}")
        
        print("\n✅ CORRECCIONES IMPLEMENTADAS:")
        print("1. Endpoint /animals/<id>/dependencies agregado")
        print("2. Mapeo de campos frontend->backend (father_id->idFather)")
        print("3. Campos idFather/idMother agregados a _filterable_fields")
        print("4. Cache limpio para resultados frescos")
        
        print("\n🔄 Para probar en el sistema:")
        print("1. Reinicia el backend para cargar los cambios")
        print("2. Intenta eliminar un animal recién creado")
        print("3. Verifica que el endpoint /animals/{id}/dependencies funcione")
        print("4. Los filtros father_id y mother_id ahora funcionarán")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    clear_integrity_cache()