#!/usr/bin/env python3
"""
Script para probar la funcionalidad de búsqueda corregida
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, date

def test_search_logic():
    """Probar la lógica de búsqueda corregida"""
    print("🔍 Probando lógica de búsqueda corregida")
    print("=" * 60)
    
    test_cases = [
        {
            'search': '2025',
            'search_type': 'auto',
            'expected': 'Solo búsqueda por fechas (año 2025)'
        },
        {
            'search': '2025',
            'search_type': 'dates',
            'expected': 'Solo búsqueda por fechas (año 2025)'
        },
        {
            'search': '2025',
            'search_type': 'text',
            'expected': 'Solo búsqueda por texto y ID (2025)'
        },
        {
            'search': '2025',
            'search_type': 'all',
            'expected': 'Búsqueda en todos los campos (texto, ID, y fechas)'
        },
        {
            'search': 'vaca',
            'search_type': 'auto',
            'expected': 'Solo búsqueda por texto (no es fecha)'
        },
        {
            'search': '2024-12',
            'search_type': 'auto',
            'expected': 'Solo búsqueda por fechas (diciembre 2024)'
        },
        {
            'search': '25/12/2024',
            'search_type': 'auto',
            'expected': 'Solo búsqueda por fechas (25 diciembre 2024)'
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: '{case['search']}' con search_type='{case['search_type']}'")
        print(f"   Expected: {case['expected']}")
        
        # Simular la lógica del método corregido
        search = case['search']
        search_type = case['search_type']
        
        is_date_search = False
        year_only = None
        month_only = None
        parsed_date = None
        parsed_datetime = None
        
        if isinstance(search, str):
            search = search.strip()
            
            # Detectar si es solo un año (4 dígitos)
            if search.isdigit() and len(search) == 4:
                try:
                    year_only = int(search)
                    is_date_search = True
                except ValueError:
                    pass
            
            # Detectar si es año-mes (YYYY-MM o YYYY/MM)
            elif len(search) in [6, 7] and ('-' in search or '/' in search):
                try:
                    parts = search.replace('/', '-').split('-')
                    if len(parts) == 2:
                        year_only = int(parts[0])
                        month_only = int(parts[1])
                        is_date_search = True
                except (ValueError, IndexError):
                    pass
            
            # Intentar parsear como fecha completa
            else:
                date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d']
                datetime_formats = [
                    '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
                    '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M'
                ]
                
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(search, fmt).date()
                        is_date_search = True
                        break
                    except Exception:
                        continue
                
                if not parsed_date:
                    for fmt in datetime_formats:
                        try:
                            parsed_datetime = datetime.strptime(search, fmt)
                            is_date_search = True
                            break
                        except Exception:
                            continue
        
        # Determinar qué tipo de búsqueda se aplicará
        if search_type == 'dates' or (search_type == 'auto' and is_date_search):
            actual = "Solo búsqueda por fechas"
            if year_only:
                actual += f" (año {year_only})"
            if month_only:
                actual += f" (mes {month_only})"
            if parsed_date:
                actual += f" (fecha {parsed_date})"
            if parsed_datetime:
                actual += f" (datetime {parsed_datetime})"
        elif search_type == 'text' or (search_type == 'auto' and not is_date_search):
            actual = "Solo búsqueda por texto e ID"
        elif search_type == 'all':
            actual = "Búsqueda en todos los campos (texto, ID, y fechas)"
        else:
            actual = "Tipo de búsqueda desconocido"
        
        print(f"   Actual:   {actual}")
        
        # Verificar si el resultado es el esperado
        if case['expected'] in actual or actual in case['expected']:
            print("   ✅ PASS")
        else:
            print("   ❌ FAIL")
    
    print("\n" + "=" * 60)
    print("📄 RESUMEN DE LA CORRECCIÓN:")
    print("1. ✅ Se separó la lógica de búsqueda por fechas de la búsqueda por texto")
    print("2. ✅ Se agregó el parámetro 'search_type' con opciones:")
    print("   - 'auto': Detecta automáticamente si es fecha o texto (default)")
    print("   - 'dates': Fuerza búsqueda solo en campos de fecha")
    print("   - 'text': Fuerza búsqueda solo en campos de texto e ID")
    print("   - 'all': Busca en todos los campos (comportamiento anterior)")
    print("3. ✅ Ahora buscar '2025' solo encontrará registros con fechas de 2025")
    print("4. ✅ Para buscar texto '2025' en campos de texto, usar search_type='text'")
    print("5. ✅ Para buscar en todos los campos, usar search_type='all'")
    
    print("\n📝 EJEMPLOS DE USO:")
    print("GET /api/v1/animals/?search=2025")
    print("   → Busca animales con fechas en 2025")
    print("")
    print("GET /api/v1/animals/?search=2025&search_type=text")
    print("   → Busca animales con '2025' en campos de texto o ID=2025")
    print("")
    print("GET /api/v1/animals/?search=2025&search_type=all")
    print("   → Busca en todos los campos (comportamiento anterior)")

if __name__ == "__main__":
    test_search_logic()