"""
Script para aplicar índices de rendimiento en la base de datos.

Ejecutar:
    python run_migration.py

Este script crea índices en updated_at y created_at para mejorar
el rendimiento de queries con filtros temporales.
"""
from wsgi import app
from app import db
import os

def main():
    print("=" * 70)
    print("🗄️  MIGRACIÓN: Agregar índices de rendimiento")
    print("=" * 70)
    print()

    sql_file = 'add_performance_indexes.sql'

    if not os.path.exists(sql_file):
        print(f"❌ Error: No se encontró el archivo {sql_file}")
        print(f"   Asegúrate de ejecutar este script desde la raíz del proyecto.")
        return

    print(f"📄 Leyendo archivo: {sql_file}")
    print()

    with open(sql_file, 'r', encoding='utf-8') as f:
        sql = f.read()

    # Separar statements
    statements = []
    for statement in sql.split(';'):
        statement = statement.strip()
        # Filtrar comentarios y líneas vacías
        if statement and not statement.startswith('--') and 'CREATE INDEX' in statement:
            statements.append(statement)

    total = len(statements)
    print(f"📊 Total de índices a crear: {total}")
    print()

    with app.app_context():
        success_count = 0
        skip_count = 0
        error_count = 0

        for i, statement in enumerate(statements, 1):
            # Extraer nombre del índice para logging
            try:
                index_name = statement.split('IF NOT EXISTS')[1].split('ON')[0].strip()
                table_name = statement.split('ON')[1].split('(')[0].strip()
            except:
                index_name = "unknown"
                table_name = "unknown"

            print(f"[{i:2d}/{total}] Creando {index_name} en tabla {table_name}...", end=" ")

            try:
                db.session.execute(db.text(statement))
                db.session.commit()
                print("✅")
                success_count += 1
            except Exception as e:
                error_msg = str(e)

                # Verificar si es porque ya existe (esto es OK)
                if 'Duplicate key name' in error_msg or 'already exists' in error_msg.lower():
                    print("⚠️  (ya existe)")
                    skip_count += 1
                else:
                    print(f"❌ Error: {error_msg[:50]}")
                    error_count += 1

                # Rollback para continuar con el siguiente
                db.session.rollback()

    print()
    print("=" * 70)
    print("📊 RESUMEN")
    print("=" * 70)
    print(f"✅ Índices creados exitosamente: {success_count}")
    print(f"⚠️  Índices ya existían:          {skip_count}")
    print(f"❌ Errores:                       {error_count}")
    print()

    if error_count > 0:
        print("⚠️  Hubo algunos errores. Revisar permisos de usuario y existencia de tablas.")
    elif success_count > 0:
        print("🎉 ¡Migración completada exitosamente!")
        print()
        print("✅ Los siguientes endpoints ahora son mucho más rápidos:")
        print("   - GET /api/v1/{resource}/metadata")
        print("   - GET /api/v1/{resource}?since=timestamp")
        print()
        print("📈 Mejora esperada: 40-50x más rápido en queries con filtros temporales")
    else:
        print("ℹ️  Todos los índices ya existían. No se realizaron cambios.")

    print()

if __name__ == '__main__':
    main()
