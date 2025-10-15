#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para probar el nuevo endpoint de estadísticas completas del dashboard
"""
import requests
import json
import time
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:5000/api/v1"
LOGIN_URL = f"{BASE_URL}/auth/login"
STATS_URL = f"{BASE_URL}/analytics/dashboard/complete"

# Credenciales de prueba (ajustar según tu configuración)
TEST_USER = {
    "username": "admin",
    "password": "admin123"
}

def login():
    """Obtener token de autenticación"""
    print("🔐 Iniciando sesión...")
    try:
        response = requests.post(LOGIN_URL, json=TEST_USER)
        if response.status_code == 200:
            data = response.json()
            token = data.get('data', {}).get('access_token') or data.get('access_token')
            print("✅ Sesión iniciada exitosamente")
            return token
        else:
            print(f"❌ Error en login: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None

def get_dashboard_stats(token):
    """Obtener estadísticas completas del dashboard"""
    print("\n📊 Obteniendo estadísticas del dashboard...")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        start_time = time.time()
        response = requests.get(STATS_URL, headers=headers)
        end_time = time.time()

        elapsed_time = (end_time - start_time) * 1000  # Convertir a ms

        if response.status_code == 200:
            data = response.json()
            stats = data.get('data', {})

            print(f"✅ Estadísticas obtenidas exitosamente")
            print(f"⏱️  Tiempo de respuesta: {elapsed_time:.2f} ms")
            print(f"\n{'='*60}")
            print("📈 RESUMEN DE ESTADÍSTICAS")
            print(f"{'='*60}\n")

            # Mostrar estadísticas principales
            print("👥 USUARIOS")
            print(f"   Registrados: {stats.get('usuarios_registrados', {}).get('valor', 0)}")
            print(f"   Activos: {stats.get('usuarios_activos', {}).get('valor', 0)}")

            print("\n🐄 ANIMALES")
            print(f"   Registrados: {stats.get('animales_registrados', {}).get('valor', 0)}")
            print(f"   Activos: {stats.get('animales_activos', {}).get('valor', 0)}")

            print("\n💊 TRATAMIENTOS")
            print(f"   Totales: {stats.get('tratamientos_totales', {}).get('valor', 0)}")
            print(f"   Activos: {stats.get('tratamientos_activos', {}).get('valor', 0)}")

            print("\n💉 VACUNAS")
            print(f"   Aplicadas: {stats.get('vacunas_aplicadas', {}).get('valor', 0)}")

            print("\n📋 CONTROLES")
            print(f"   Realizados: {stats.get('controles_realizados', {}).get('valor', 0)}")

            print("\n🚨 ALERTAS Y TAREAS")
            print(f"   Alertas: {stats.get('alertas_sistema', {}).get('valor', 0)}")
            alertas_desglose = stats.get('alertas_sistema', {}).get('desglose', {})
            if alertas_desglose:
                print(f"      - Sin control: {alertas_desglose.get('animales_sin_control', 0)}")
                print(f"      - Sin vacunación: {alertas_desglose.get('animales_sin_vacunacion', 0)}")
                print(f"      - Salud crítica: {alertas_desglose.get('estado_salud_critico', 0)}")
            print(f"   Tareas pendientes: {stats.get('tareas_pendientes', {}).get('valor', 0)}")

            print("\n📍 CAMPOS Y RELACIONES")
            print(f"   Campos registrados: {stats.get('campos_registrados', {}).get('valor', 0)}")
            print(f"   Animales por campo: {stats.get('animales_por_campo', {}).get('valor', 0)}")
            print(f"   Animales por enfermedad: {stats.get('animales_por_enfermedad', {}).get('valor', 0)}")

            print("\n📚 CATÁLOGOS")
            print(f"   Vacunas: {stats.get('catalogo_vacunas', {}).get('valor', 0)}")
            print(f"   Medicamentos: {stats.get('catalogo_medicamentos', {}).get('valor', 0)}")
            print(f"   Enfermedades: {stats.get('catalogo_enfermedades', {}).get('valor', 0)}")
            print(f"   Especies: {stats.get('catalogo_especies', {}).get('valor', 0)}")
            print(f"   Razas: {stats.get('catalogo_razas', {}).get('valor', 0)}")
            print(f"   Tipos de alimento: {stats.get('catalogo_tipos_alimento', {}).get('valor', 0)}")

            print("\n🧬 MEJORAS Y TRATAMIENTOS ESPECIALIZADOS")
            print(f"   Mejoras genéticas: {stats.get('mejoras_geneticas', {}).get('valor', 0)}")
            print(f"   Tratamientos con medicamentos: {stats.get('tratamientos_con_medicamentos', {}).get('valor', 0)}")
            print(f"   Tratamientos con vacunas: {stats.get('tratamientos_con_vacunas', {}).get('valor', 0)}")

            # Metadata
            metadata = stats.get('metadata', {})
            print(f"\n{'='*60}")
            print("ℹ️  METADATA")
            print(f"{'='*60}")
            print(f"   Generado en: {metadata.get('generado_en', 'N/A')}")
            print(f"   Versión: {metadata.get('version', 'N/A')}")
            print(f"   Optimizado: {metadata.get('optimizado', False)}")
            print(f"   Cache TTL: {metadata.get('cache_ttl', 0)} segundos")

            print(f"\n{'='*60}\n")

            # Guardar respuesta completa en archivo JSON
            with open('dashboard_stats_response.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("💾 Respuesta completa guardada en: dashboard_stats_response.json")

            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_cache_performance(token):
    """Probar el rendimiento del caché"""
    print("\n🔄 Probando rendimiento del caché...")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    times = []

    for i in range(3):
        print(f"\n   Petición {i+1}/3...")
        start_time = time.time()
        response = requests.get(STATS_URL, headers=headers)
        end_time = time.time()

        elapsed_time = (end_time - start_time) * 1000
        times.append(elapsed_time)

        if response.status_code == 200:
            print(f"   ✅ Tiempo: {elapsed_time:.2f} ms")
        else:
            print(f"   ❌ Error: {response.status_code}")

    if times:
        print(f"\n{'='*60}")
        print("📊 ANÁLISIS DE RENDIMIENTO")
        print(f"{'='*60}")
        print(f"   Primera petición (sin caché): {times[0]:.2f} ms")
        if len(times) > 1:
            print(f"   Segunda petición (con caché): {times[1]:.2f} ms")
            print(f"   Tercera petición (con caché): {times[2]:.2f} ms")
            print(f"\n   Mejora de rendimiento: {((times[0] - times[1]) / times[0] * 100):.1f}%")
        print(f"{'='*60}\n")

def main():
    """Función principal"""
    print(f"\n{'='*60}")
    print("🧪 TEST DE ESTADÍSTICAS COMPLETAS DEL DASHBOARD")
    print(f"{'='*60}\n")
    print(f"Servidor: {BASE_URL}")
    print(f"Endpoint: {STATS_URL}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n{'='*60}\n")

    # Login
    token = login()
    if not token:
        print("\n❌ No se pudo obtener el token de autenticación")
        print("Asegúrate de que:")
        print("  1. El servidor esté corriendo (python run.py)")
        print("  2. Las credenciales sean correctas")
        return

    # Obtener estadísticas
    success = get_dashboard_stats(token)

    if success:
        # Probar rendimiento del caché
        test_cache_performance(token)

        print("\n✅ ¡Prueba completada exitosamente!")
        print("\n💡 PRÓXIMOS PASOS:")
        print("   1. Actualizar el frontend para consumir este endpoint")
        print("   2. Usar GET /api/v1/analytics/dashboard/complete")
        print("   3. El caché se actualiza cada 2 minutos automáticamente")
        print(f"\n{'='*60}\n")
    else:
        print("\n❌ La prueba falló. Revisa los errores anteriores.")

if __name__ == "__main__":
    main()
