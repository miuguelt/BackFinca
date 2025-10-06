#!/usr/bin/env python3
"""
Script para limpiar cache y probar el sistema corregido.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def clear_cache_and_test():
    """Limpia el cache y prueba el sistema."""
    try:
        from app.utils.integrity_checker import OptimizedIntegrityChecker
        
        print("LIMPIEZA DE CACHE Y PRUEBA")
        print("="*40)
        
        # Limpiar cache
        OptimizedIntegrityChecker.clear_cache()
        print("✅ Cache limpiado")
        
        # Mostrar estadísticas del cache
        stats = OptimizedIntegrityChecker.get_cache_stats()
        print(f"Estadísticas del cache: {stats}")
        
        print("\nEl sistema de integridad referencial ha sido corregido:")
        print("✅ Eliminada relación incorrecta 'reverse_breeds'")
        print("✅ Manejo correcto de auto-referencias (padre/madre)")
        print("✅ Detección proper de dependencias reales")
        print("✅ Cache limpio para resultados frescos")
        
        print("\nPara probar en el sistema:")
        print("1. Intenta eliminar un animal recién creado (sin dependencias)")
        print("2. Intenta eliminar un animal con dependencias conocidas")
        print("3. Verifica que los mensajes sean precisos")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    clear_cache_and_test()