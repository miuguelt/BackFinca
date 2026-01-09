# Guía Paso a Paso de Migraciones (Alembic / Flask-Migrate)

Esta guía define un flujo estándar y reproducible para crear, aplicar y verificar migraciones de base de datos en BackFinca usando Flask-Migrate (Alembic). Incluye comandos listos para Windows PowerShell y Linux/macOS.

## Comando único recomendado
- Ejecutar y verificar migraciones de forma robusta:
  - `python upgrade_db.py`
- Este comando:
  - Carga variables de entorno desde `.env`.
  - Verifica conexión a la base de datos.
  - Ejecuta `upgrade head` con Alembic.
  - Verifica índices críticos y crea los faltantes.
  - Muestra la revisión final aplicada.

## Objetivo
- Unificar cómo se crean y ejecutan migraciones.
- Evitar errores comunes (índices duplicados, `down_revision`, conexiones).
- Asegurar verificación y rollback controlado.

## Prerrequisitos
- Python instalado y dependencias del proyecto:
  - Windows:
    - `python -m venv .venv && .\\.venv\\Scripts\\Activate.ps1`
    - `pip install -r requirements.txt`
  - Linux/macOS:
    - `python -m venv .venv && source .venv/bin/activate`
    - `pip install -r requirements.txt`
- Variables de entorno definidas:
  - FLASK_ENV
  - SQLALCHEMY_DATABASE_URI
  - JWT_SECRET_KEY

Sugerencia: definir un archivo `.env` (no se sube al repo) con:
```
FLASK_ENV=development
JWT_SECRET_KEY=<clave-segura-larga>
SQLALCHEMY_DATABASE_URI=mysql+pymysql://usuario:password@host:puerto/base
```

## Comandos esenciales
- Ver estado actual:
  - Windows: `python -m flask --app wsgi db current`
  - Linux/macOS: `FLASK_APP=wsgi.py flask db current`
- Ver historial:
  - Windows: `python -m flask --app wsgi db history`
  - Linux/macOS: `FLASK_APP=wsgi.py flask db history`
- Generar nueva migración (después de cambiar modelos):
  - Windows: `python -m flask --app wsgi db migrate -m "Descripcion de la migracion"`
  - Linux/macOS: `FLASK_APP=wsgi.py flask db migrate -m "Descripcion de la migracion"`
- Aplicar migraciones:
  - Windows: `python -m flask --app wsgi db upgrade`
  - Linux/macOS: `FLASK_APP=wsgi.py flask db upgrade`
- Revertir (rollback):
  - Un paso: `python -m flask --app wsgi db downgrade -1`
  - A revisión exacta: `python -m flask --app wsgi db downgrade <revision_id>`

## Flujo estándar para crear y aplicar una nueva migración
1. Preparar entorno:
   - Windows PowerShell:
     - `pip install -r requirements.txt`
     - `Set-Item -Path Env:FLASK_ENV -Value "development"`
     - `Set-Item -Path Env:JWT_SECRET_KEY -Value "<clave-segura>"`
     - `Set-Item -Path Env:SQLALCHEMY_DATABASE_URI -Value "mysql+pymysql://usuario:password@host:puerto/base"`
   - Linux/macOS:
     - `export FLASK_ENV=development`
     - `export JWT_SECRET_KEY="<clave-segura>"`
     - `export SQLALCHEMY_DATABASE_URI="mysql+pymysql://usuario:password@host:puerto/base"`
2. Verificar estado actual:
   - `python -m flask --app wsgi db current`
3. Modificar modelos SQLAlchemy en `app/models/` según necesidad.
4. Autogenerar migración:
   - `python -m flask --app wsgi db migrate -m "Descripcion clara"`
5. Revisar el archivo generado en `migrations/versions/`:
   - Confirmar `revision` y `down_revision`.
   - Ajustar lógica si es necesario (evitar duplicados de índices mediante inspección).
6. Aplicar:
   - `python -m flask --app wsgi db upgrade`
7. Validar:
   - `python -m flask --app wsgi db current` debe mostrar la revisión en head.
   - Comprobar índices/tablas según la migración (ver sección Verificación).

## Verificación y rollback
- MySQL: comprobar índices
  ```
  SHOW INDEX FROM animals WHERE Key_name LIKE 'ix_%';
  SHOW INDEX FROM activity_log WHERE Key_name LIKE 'ix_%';
  ```
- SQLite/Postgres: usar EXPLAIN para confirmar uso de índices.
- Si algo falla:
  - `python -m flask --app wsgi db downgrade -1`
  - Ajustar el archivo en `migrations/versions/` y volver a `upgrade`.

## Convenciones y buenas prácticas
- Mensajes claros de migración: usar verbos y contexto (“add”, “normalize”, “make_not_null”, “composite_index”).
- Evitar índices duplicados:
  - Usar inspección de índices antes de crear:
    - Ver ejemplo en [20260108_activity_agg_and_indexes.py](file:///c:/Users/Miguel/Documents/Flask%20Projects/BackFinca/migrations/versions/20260108_activity_agg_and_indexes.py#L20-L31).
- Mantener cadena de revisiones:
  - `down_revision` debe apuntar al último ID aplicado.
- Verificar en entorno de pruebas antes de producción.

## Problemas frecuentes y soluciones
- “Index already exists”:
  - Comentar/ajustar creación en la migración o usar inspección para crear solo si no existe.
  - Secuencia: `flask db downgrade` y `flask db upgrade` si quedó en estado inconsistente.
- “down_revision not found”:
  - Ejecutar `flask db current`, tomar ese ID, y actualizar `down_revision` en el archivo.
- “Can't connect to MySQL server”:
  - Verificar servicio, host/puerto/credenciales en `.env`.
  - Validar firewall y reachability.
- Redis no disponible:
  - El backend usa fallback a SimpleCache y rate-limit en memoria; no bloquea migraciones.

## Archivos clave del flujo
- Inicialización de Flask-Migrate: [__init__.py](file:///c:/Users/Miguel/Documents/Flask%20Projects/BackFinca/app/__init__.py#L248-L252)
- Integración Alembic con la app: [env.py](file:///c:/Users/Miguel/Documents/Flask%20Projects/BackFinca/migrations/env.py#L11-L20) y [env.py](file:///c:/Users/Miguel/Documents/Flask%20Projects/BackFinca/migrations/env.py#L29-L41)
- Configuración Alembic: [alembic.ini](file:///c:/Users/Miguel/Documents/Flask%20Projects/BackFinca/alembic.ini)
- Ejemplo de migración con inspección de índices: [20260108_activity_agg_and_indexes.py](file:///c:/Users/Miguel/Documents/Flask%20Projects/BackFinca/migrations/versions/20260108_activity_agg_and_indexes.py)

## Ejemplo rápido (Windows PowerShell)
```
Set-Item Env:FLASK_ENV "development"
Set-Item Env:JWT_SECRET_KEY "clave-super-segura-larga"
Set-Item Env:SQLALCHEMY_DATABASE_URI "mysql+pymysql://usuario:password@host:puerto/base"

python -m flask --app wsgi db current
python -m flask --app wsgi db migrate -m "Agregar indices actividad"
python -m flask --app wsgi db upgrade
python -m flask --app wsgi db current
```

## Notas
- No subir `.env` ni secretos al repositorio.
- En producción, ejecutar `upgrade` antes de iniciar la nueva versión de la app.
- Mantener esta guía en `docs/migrations/` para uso del equipo.
