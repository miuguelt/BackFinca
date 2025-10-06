#!/usr/bin/env python3
"""
Script para verificar la lógica del integrity checker sin DB.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_logic_only():
    """Prueba solo la lógica del integrity checker."""
    try:
        from app.models.animals import Animals
        from app.utils.integrity_checker import OptimizedIntegrityChecker
        
        print("VERIFICACIÓN DE LÓGICA DEL INTEGRITY CHECKER")
        print("="*50)
        
        # Analizar las relaciones detectadas
        relationships = OptimizedIntegrityChecker._get_model_relationships(Animals)
        
        print(f"\nRelaciones detectadas: {len(relationships)}")
        
        # Verificar que no haya relaciones inversas incorrectas
        reverse_rels = [rel for rel in relationships if rel.get('reverse')]
        self_refs = [rel for rel in relationships if rel['target_table'] == Animals.__tablename__]
        forward_rels = [rel for rel in relationships if not rel.get('reverse') and rel['target_table'] != Animals.__tablename__]
        
        print(f"  - Relaciones inversas: {len(reverse_rels)}")
        print(f"  - Auto-referencias: {len(self_refs)}")
        print(f"  - Relaciones directas: {len(forward_rels)}")
        
        # Mostrar detalles
        print("\nAuto-referencias (padre/madre):")
        for rel in self_refs:
            print(f"  - {rel['name']}: {rel['foreign_keys']}")
        
        print("\nRelaciones directas:")
        for rel in forward_rels:
            print(f"  - {rel['name']} -> {rel['target_table']}")
        
        print("\nRelaciones inversas:")
        for rel in reverse_rels:
            print(f"  - {rel['name']} -> {rel['target_table']}")
        
        # Verificar que no haya la relación incorrecta 'reverse_breeds'
        reverse_breeds = [rel for rel in relationships if rel['name'] == 'reverse_breeds']
        if reverse_breeds:
            print(f"\n❌ ERROR: Todavía existe la relación incorrecta 'reverse_breeds'")
            return False
        else:
            print(f"\n✅ CORRECTO: No existe la relación incorrecta 'reverse_breeds'")
        
        # Verificar que las auto-referencias se manejen correctamente
        expected_self_refs = ['father', 'mother']
        actual_self_refs = [rel['name'] for rel in self_refs]
        
        if set(expected_self_refs) == set(actual_self_refs):
            print(f"✅ CORRECTO: Auto-referencias detectadas correctamente: {actual_self_refs}")
        else:
            print(f"❌ ERROR: Auto-referencias incorrectas. Esperadas: {expected_self_refs}, Detectadas: {actual_self_refs}")
            return False
        
        # Simular el procesamiento de dependencias
        print(f"\nSIMULACIÓN DE PROCESAMIENTO:")
        test_id = 123
        
        # Separar relaciones como lo hace el método real
        reverse_deps = []
        forward_deps = []
        self_refs_processed = []
        
        for rel in relationships:
            if rel.get('reverse'):
                reverse_deps.append(rel)
            elif rel['target_table'] == Animals.__tablename__:
                self_refs_processed.append(rel)
            else:
                forward_deps.append(rel)
        
        print(f"  - Dependencias inversas: {len(reverse_deps)}")
        print(f"  - Auto-referencias: {len(self_refs_processed)}")
        print(f"  - Dependencias directas: {len(forward_deps)}")
        
        # Verificar campos para auto-referencias
        for rel in self_refs_processed:
            field_name = rel['foreign_keys'][0] if rel['foreign_keys'] else f"{Animals.__tablename__}_id"
            print(f"    * {rel['name']} usará campo: {field_name}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_logic_only()
    if success:
        print(f"\n✅ VERIFICACIÓN EXITOSA - La lógica parece correcta")
    else:
        print(f"\n❌ ERRORES ENCONTRADOS - Revisar la lógica")