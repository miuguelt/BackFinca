#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad de búsqueda por año, mes, día y todas las columnas
"""

from app import create_app, db
from app.models.animals import Animals
from app.models.treatments import Treatments
from app.models.vaccinations import Vaccinations
from app.models.control import Control
from app.models.animalDiseases import AnimalDiseases
from app.models.geneticImprovements import GeneticImprovements
from datetime import date, datetime

def test_search_functionality():
    """Probar la funcionalidad de búsqueda mejorada"""
    app = create_app()
    
    with app.app_context():
        print("🔍 Probando funcionalidad de búsqueda mejorada...")
        
        # Modelos a probar
        models_to_test = [
            ('Animals', Animals),
            ('Treatments', Treatments),
            ('Vaccinations', Vaccinations),
            ('Control', Control),
            ('AnimalDiseases', AnimalDiseases),
            ('GeneticImprovements', GeneticImprovements)
        ]
        
        for model_name, model_class in models_to_test:
            print(f"\n📋 Probando búsqueda en {model_name}:")
            
            # Probar búsqueda por año actual
            current_year = date.today().year
            year_query = model_class.get_namespace_query(search=str(current_year))
            year_count = year_query.count() if hasattr(year_query, 'count') else len(year_query.all())
            print(f"  📅 Búsqueda por año {current_year}: {year_count} resultados")
            
            # Probar búsqueda por mes actual
            current_month = date.today().month
            month_search = f"{current_year}-{current_month:02d}"
            month_query = model_class.get_namespace_query(search=month_search)
            month_count = month_query.count() if hasattr(month_query, 'count') else len(month_query.all())
            print(f"  📅 Búsqueda por mes {month_search}: {month_count} resultados")
            
            # Probar búsqueda por fecha específica
            today = date.today().strftime('%Y-%m-%d')
            today_query = model_class.get_namespace_query(search=today)
            today_count = today_query.count() if hasattr(today_query, 'count') else len(today_query.all())
            print(f"  📅 Búsqueda por fecha {today}: {today_count} resultados")
            
            # Probar búsqueda de texto en todas las columnas
            text_query = model_class.get_namespace_query(search="a")
            text_count = text_query.count() if hasattr(text_query, 'count') else len(text_query.all())
            print(f"  🔤 Búsqueda de texto 'a' en todas las columnas: {text_count} resultados")
            
            # Probar búsqueda por ID
            if model_class.query.first():
                first_id = model_class.query.first().id
                id_query = model_class.get_namespace_query(search=str(first_id))
                id_count = id_query.count() if hasattr(id_query, 'count') else len(id_query.all())
                print(f"  🔢 Búsqueda por ID {first_id}: {id_count} resultados")
        
        print("\n✅ Pruebas de búsqueda completadas exitosamente!")
        
        # Mostrar información para el frontend
        print("\n📄 Información para el frontend:")
        print("El backend ahora soporta los siguientes tipos de búsqueda:")
        print("1. 📅 Por año: '2024' (busca en todas las columnas de fecha)")
        print("2. 📅 Por mes: '2024-12' o '2024/12' (busca registros de ese mes)")
        print("3. 📅 Por día: '2024-12-25' o '25/12/2024' (fecha específica)")
        print("4. 🔤 Por texto: busca en TODAS las columnas de texto del modelo")
        print("5. 🔢 Por ID: búsqueda exacta por ID numérico")
        print("\nLa búsqueda se aplica automáticamente a todas las columnas de fecha y texto de cada modelo.")

if __name__ == "__main__":
    test_search_functionality()