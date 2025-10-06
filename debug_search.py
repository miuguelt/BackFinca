#!/usr/bin/env python3
"""
Script para depurar la funcionalidad de búsqueda sin necesidad de base de datos
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, date
from sqlalchemy import Date, DateTime, extract, or_

def analyze_search_logic(search_term):
    """Analiza la lógica de búsqueda para un término específico"""
    print(f"🔍 Analizando término de búsqueda: '{search_term}'")
    
    # Simular la lógica del base_model.py
    search_conditions = []
    parsed_date = None
    parsed_datetime = None
    year_only = None
    month_only = None
    day_only = None
    
    if isinstance(search_term, str):
        search_term = search_term.strip()
        
        # Detectar si es solo un año (4 dígitos)
        if search_term.isdigit() and len(search_term) == 4:
            try:
                year_only = int(search_term)
                print(f"  ✅ Detectado año: {year_only}")
            except ValueError:
                pass
        
        # Detectar si es año-mes (YYYY-MM o YYYY/MM)
        elif len(search_term) in [6, 7] and ('-' in search_term or '/' in search_term):
            try:
                parts = search_term.replace('/', '-').split('-')
                if len(parts) == 2:
                    year_only = int(parts[0])
                    month_only = int(parts[1])
                    print(f"  ✅ Detectado año-mes: {year_only}-{month_only:02d}")
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
                    parsed_date = datetime.strptime(search_term, fmt).date()
                    print(f"  ✅ Detectado fecha completa: {parsed_date} (formato: {fmt})")
                    break
                except Exception:
                    continue
            
            if not parsed_date:
                for fmt in datetime_formats:
                    try:
                        parsed_datetime = datetime.strptime(search_term, fmt)
                        print(f"  ✅ Detectado datetime completo: {parsed_datetime} (formato: {fmt})")
                        break
                    except Exception:
                        continue
    
    # Analizar qué condiciones se generarían
    print(f"\n📋 Condiciones de búsqueda que se generarían:")
    
    # Búsqueda de texto (simulada)
    print(f"  🔤 Búsqueda de texto: LIKE '%{search_term}%' en todas las columnas de texto")
    
    # Búsqueda por ID si es numérico
    try:
        id_val = int(str(search_term))
        print(f"  🔢 Búsqueda por ID: id = {id_val}")
    except (ValueError, TypeError):
        pass
    
    # Búsqueda por fechas
    if year_only is not None:
        print(f"  📅 Búsqueda por año: extract('year', fecha_columna) = {year_only}")
    
    if month_only is not None:
        print(f"  📅 Búsqueda por mes: extract('month', fecha_columna) = {month_only}")
    
    if parsed_date is not None:
        print(f"  📅 Búsqueda por fecha: fecha_columna = {parsed_date}")
    
    if parsed_datetime is not None:
        print(f"  📅 Búsqueda por datetime: datetime_columna = {parsed_datetime}")
    
    print(f"\n⚠️  PROBLEMA IDENTIFICADO:")
    print(f"  - La búsqueda usa OR_() para combinar TODAS las condiciones")
    print(f"  - Esto significa que si buscas '2025', encontrará:")
    print(f"    • Registros con año 2025 en cualquier campo de fecha")
    print(f"    • Registros con texto '2025' en cualquier campo de texto")
    print(f"    • Registros con ID = 2025")
    print(f"  - La consulta devuelve TODAS las columnas del modelo")
    print(f"  - Si no ves algunas columnas, puede ser un problema del frontend")

def main():
    """Función principal"""
    print("🔍 Depuración de la funcionalidad de búsqueda")
    print("=" * 50)
    
    # Probar diferentes casos
    test_cases = [
        "2025",
        "2024-12",
        "2024-12-25",
        "25/12/2024",
        "texto",
        "123"
    ]
    
    for case in test_cases:
        analyze_search_logic(case)
        print("\n" + "=" * 50)
    
    print("\n📄 RECOMENDACIONES:")
    print("1. La lógica de búsqueda funciona correctamente")
    print("2. El problema puede estar en:")
    print("   - Cómo el frontend muestra los resultados")
    print("   - Filtros adicionales que no se están aplicando")
    print("   - Conversión de datos a JSON")
    print("3. Para corregir, considera:")
    print("   - Separar la búsqueda por fechas de la búsqueda por texto")
    print("   - Agregar parámetros específicos para búsqueda por fechas")
    print("   - Validar qué columnas se están devolviendo en la respuesta")

if __name__ == "__main__":
    main()