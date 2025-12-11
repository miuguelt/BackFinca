# Guía completa del backend – Programa ADSO (SENA)

Guía pedagógica y práctica para entender, extender y mantener el backend de Finca Villaluz. Escrita en español claro para aprendices ADSO.

---

## 1) Visión general y estructura del proyecto

El backend es una API REST construida con Flask + Flask-RESTX, organizada en módulos claros: entrada, API, namespaces (controladores), modelos, utilidades, migraciones y recursos estáticos.

```
run.py / wsgi.py   ← Puntos de entrada (dev/prod)
config.py          ← Configuración por entorno
app/
  ├─ __init__.py   ← create_app: inicializa extensiones, middlewares, CORS, JWT, cache, rate limit
  ├─ api.py        ← Blueprint /api/v1, documentación Swagger y registro de namespaces
  ├─ namespaces/   ← Endpoints por recurso (CRUD + lógica extra)
  ├─ models/       ← Modelos SQLAlchemy; heredan de BaseModel con validaciones y metadatos
  ├─ utils/        ← Utilidades transversales (JWT, cache, seguridad, respuestas, archivos, etc.)
  └─ templates/    ← Plantillas HTML para Swagger UI y guías
migrations/        ← Alembic (versionado de esquema)
static/            ← Archivos subidos (imágenes, etc.) servidos públicamente
scripts/           ← Herramientas de soporte (smoke tests, generación de rutas, seeds, etc.)
docs/              ← Documentación adicional (Markdown)
tests (test_*.py)  ← Pruebas rápidas con pytest (en raíz)
```

### Archivos raíz clave
- `run.py`: arranque en desarrollo; carga `.env`, crea la app, aplica ProxyFix, HTTPS opcional, headers de seguridad, `db.create_all()` en dev.
- `wsgi.py`: arranque en producción (Gunicorn/WSGI); carga `.env.production` si aplica, fuerza configuraciones seguras (CSP, HSTS), valida variables críticas (JWT).
- `config.py`: clases `DevelopmentConfig`, `ProductionConfig`, `TestingConfig`. Define DB, Redis cache, JWT, CORS, límites, logging. Usa variables de entorno; en prod obliga `JWT_SECRET_KEY` y `JWT_COOKIE_DOMAIN`.

### app/__init__.py (create_app)
- Inicializa extensiones: `db`, `jwt`, `cache`, `migrate`.
- Configura JSON encoder para enums/fechas, CORS, logging, rate limiter, middlewares de seguridad.
- Registra rutas públicas (`/`, `/health`, `/public/images/*`, `/static/*`) y redirecciones de docs.
- Llama a `register_api` (app/api.py) para registrar todos los namespaces bajo `/api/v1`.
- Ejecuta bootstrap: usuario admin semilla, warmup de caché.

### app/api.py
- Crea blueprint `/api/v1` y objeto `Api` (Flask-RESTX) con Swagger UI personalizado (`app/templates/swagger_ui_custom.html`).
- Registra namespaces de recursos (auth, users, animals, analytics, etc.).
- Endpoints utilitarios: `/api/v1/health`, `/api/v1/docs/schema` (metadatos de modelos), `/api/v1/docs/examples`, `/api/v1/docs/guia-frontend`.

### Namespaces (app/namespaces/)
- Un archivo por recurso: `animals_namespace.py`, `users_namespace.py`, `vaccines_namespace.py`, etc.
- La mayoría usan el factory `create_optimized_namespace` (app/utils/namespace_helpers.py) que genera CRUD completo: lista con filtros/búsqueda/paginación, creación, detalle, actualización, borrado, bulk, stats (si aplica).
- Algunos namespaces incluyen endpoints extra (ej. genealogía de animales, imágenes, analítica).

### Modelos (app/models/)
- Modelos SQLAlchemy heredan de `BaseModel` y declaran:
  - Campos de tabla e índices.
  - Metadatos para el CRUD: `_namespace_fields`, `_filterable_fields`, `_searchable_fields`, `_sortable_fields`, `_required_fields`, `_unique_fields`, `_enum_fields`, `_namespace_relations`, `_cache_config`.
  - Validaciones adicionales en `_validate_and_normalize`.
  - Serialización consistente con `to_namespace_dict`.

### Utils (app/utils/)
- `namespace_helpers.py`: genera namespaces CRUD; maneja filtros, búsqueda, paginación, cache LRU, modelos Swagger, ETags.
- `response_handler.py`: respuestas estandarizadas (`success/error/paginated_success`).
- `jwt_handlers.py`, `security_middleware.py`, `rate_limiter.py`, `cors_setup.py`, `logging_config.py`, `db_optimization.py`.
- `file_storage.py`: manejo seguro de archivos subidos (imágenes).
- `json_utils.py`, `enum_registry.py`: serialización robusta.
- `bootstrap.py`: seed admin y warmup de caché.

### Migraciones (migrations/)
- `env.py` integra la app para generar/ejecutar migraciones Alembic. Archivos en `migrations/versions/`.

### Recursos estáticos y docs
- `static/uploads/...`: imágenes de animales servidas en `/static/*` y `/public/images/*`.
- `templates/`: vistas HTML para Swagger y guías.
- `docs/`: documentación adicional Markdown.

---

## 2) Flujo general de la aplicación

```
Cliente (React/PWA) → HTTPS → run.py / wsgi.py → Flask app
    → Blueprint /api/v1 (Flask-RESTX Api)
        → Namespace (Resource/CRUD generado por factory)
            → BaseModel / SQLAlchemy → MySQL/SQLite
        ↘ Utils (JWT, CORS, rate limit, cache, responses)
```

1. Arranque: `run.py`/`wsgi.py` cargan `.env`, seleccionan config y crean la app (`create_app`).
2. `create_app` inicializa extensiones, middlewares, CORS, JWT, cache, rate limiter y registra el blueprint `/api/v1`.
3. `register_api` agrega todos los namespaces (auth, animals, analytics, etc.) y expone Swagger (`/api/v1/docs/`) y el JSON (`/api/v1/swagger.json`).
4. Cada petición pasa por ProxyFix, CORS, middlewares de seguridad, rate limit (si está habilitado).
5. Namespaces usan `BaseModel` y las utilidades para validar, consultar y responder con `APIResponse`.
6. Respuestas estandarizadas: `{"success": true/false, "data": ..., "message": "...", "meta": {...}}`.

---

## 3) Cómo leer la estructura carpeta por carpeta

- `run.py`: dev server; HTTPS opcional adhoc; cabeceras de seguridad; health y create_all en dev.
- `wsgi.py`: producción; valida secretos; CSP/HSTS; no usa debugger; se ejecuta con Gunicorn/WSGI.
- `config.py`: configuración central. En prod exige `JWT_SECRET_KEY`, `JWT_COOKIE_DOMAIN`; define Redis, CORS, pool de DB, límites y logging.
- `app/__init__.py`: función `create_app`. Registra CORS, JWT, rate limiter, security middlewares, logging; rutas públicas (`/`, `/health`, `/public/images/*`, `/static/*`); redirecciones a docs; bootstrap y warmup.
- `app/api.py`: blueprint `/api/v1`, registro de namespaces, Swagger UI custom, endpoints de metadatos y guía frontend.
- `app/namespaces/`: controladores por recurso. Usan `create_optimized_namespace` para CRUD y añaden endpoints específicos si hace falta.
- `app/models/`: entidades (Animals, Breeds, Users, etc.). Incluyen enums, validaciones, índices y metadatos para búsqueda/filtros/orden/paginación.
- `app/utils/`: piezas reutilizables (cache LRU para listados, respuestas, validadores, JWT, seguridad, manejo de archivos, encoders).
- `app/templates/`: HTML para Swagger, guía frontend, tester.
- `migrations/`: scripts Alembic del esquema.
- `static/`: assets subidos (imágenes).
- `scripts/`: herramientas (smoke tests, generación de rutas desde Swagger, seeds masivos, validación de seguridad).
- `tests test_*.py`: pruebas rápidas con pytest (endpoints, imágenes, búsqueda, integridad).

---

## 4) Patrón de trabajo de los namespaces (CRUD)

- Se generan con `create_optimized_namespace(name, description, model_class, path)`:
  - GET lista: soporta filtros (?campo=valor), búsqueda (?search=texto), orden (?sort_by=&sort_order=), paginación (?page=&limit=), relaciones (`include_relations=true`).
  - GET detalle `/id`.
  - POST crea, PUT/PATCH actualiza, DELETE elimina.
  - Opcional: `/bulk`, `/stats` si el modelo lo soporta.
- Se apoyan en metadatos del modelo (`_filterable_fields`, `_searchable_fields`, `_sortable_fields`, `_required_fields`, `_enum_fields`, `_namespace_relations`).
- Cache LRU ligera por modelo con TTL configurable en `_cache_config`; invalidar con `_cache_clear(Model)` tras mutaciones.

---

## 5) Cómo crear una nueva funcionalidad (CRUD “Corrales”)

### 5.1 Análisis
- Entidad “Corrales” con: `name` (único), `capacity` (int > 0), `location` (opcional), `status` (enum: Activo/Inactivo).
- Recurso público cacheable (lecturas) y protegido por JWT para escribir.

### 5.2 Modelo (`app/models/barns.py`)
```python
from app import db
import enum
from app.models.base_model import BaseModel, ValidationError

class BarnStatus(enum.Enum):
    Activo = 'Activo'
    Inactivo = 'Inactivo'

class Barns(BaseModel):
    __tablename__ = 'barns'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    capacity = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Enum(BarnStatus), default=BarnStatus.Activo, nullable=False)

    _namespace_fields = ['id', 'name', 'capacity', 'location', 'status', 'created_at', 'updated_at']
    _filterable_fields = ['status', 'capacity']
    _searchable_fields = ['name', 'location']
    _sortable_fields = ['name', 'capacity', 'created_at', 'updated_at']
    _required_fields = ['name', 'capacity']
    _unique_fields = ['name']
    _enum_fields = {'status': BarnStatus}
    _cache_config = {'ttl': 120, 'type': 'public'}

    @classmethod
    def _validate_and_normalize(cls, data, is_update=False, instance_id=None):
        if 'capacity' in data and (data['capacity'] is None or int(data['capacity']) <= 0):
            raise ValidationError("La capacidad debe ser mayor que cero")
        return super()._validate_and_normalize(data, is_update, instance_id)
```

### 5.3 Migración Alembic
- Generar y aplicar:
```
FLASK_APP=run.py FLASK_ENV=development flask db migrate -m "add barns"
FLASK_APP=run.py FLASK_ENV=development flask db upgrade
```

### 5.4 Namespace (`app/namespaces/barns_namespace.py`)
```python
from app.utils.namespace_helpers import create_optimized_namespace
from app.models.barns import Barns

barns_ns = create_optimized_namespace(
    name='barns',
    description='Gestión de corrales',
    model_class=Barns,
    path='/barns'
)
```

### 5.5 Registrar el namespace en la API (`app/api.py`)
```python
from .namespaces.barns_namespace import barns_ns
...
api.add_namespace(barns_ns)
```

### 5.6 Probar
- Manual:
```
curl -k -X POST https://localhost:8081/api/v1/barns/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Corral A","capacity":10,"status":"Activo"}'
```
- Explorar en `/api/v1/docs/` (Swagger) que aparezca el namespace y modelos.

### 5.7 Prueba rápida (pytest)
```python
import pytest
from app import create_app, db

@pytest.fixture
def client():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
    return app.test_client()

def test_create_and_list_barns(client):
    res = client.post('/api/v1/barns/', json={'name': 'Corral A', 'capacity': 10})
    assert res.status_code == 201
    res_list = client.get('/api/v1/barns/?search=Corral')
    assert res_list.status_code == 200
    assert res_list.get_json()['meta']['pagination']['total_items'] >= 1
```
- Ejecuta: `pytest -q test_barns_namespace.py`

---

## 6) Buenas prácticas para mantener el código limpio y coherente
- Reutiliza el factory `create_optimized_namespace` para CRUD estándar; solo crea `Resource` manual cuando la lógica sea especial.
- Declara metadatos en el modelo: `_filterable_fields`, `_searchable_fields`, `_sortable_fields`, `_required_fields`, `_unique_fields`, `_enum_fields`, `_namespace_relations`.
- Valida en `_validate_and_normalize` y lanza `ValidationError` con mensajes claros.
- Usa `APIResponse.success/error/paginated_success`; evita `jsonify` directo en endpoints nuevos.
- Enums para estados, no strings mágicos.
- Cache: define `_cache_config` y limpia con `_cache_clear(Model)` tras POST/PUT/DELETE.
- Migraciones siempre: agrega modelo → genera migración → `upgrade`. No dependas de `db.create_all` en prod.
- Variables sensibles en `.env` (no las subas al repo). Provee `.env.example`.
- Logging: usa `logging.getLogger(__name__)`; no imprimas secretos. Respeta niveles en `config.py`.
- Pruebas: mínimo una prueba funcional para cada recurso nuevo; usa `create_app('testing')` y `db.create_all()` en fixtures.

---

## 7) Errores comunes y cómo evitarlos
- No registrar el namespace en `app/api.py` → el endpoint no aparece en `/docs`.
- Olvidar migraciones tras añadir campos/modelos → errores “tabla/columna no existe”.
- No definir `_required_fields`/`_enum_fields` → validación débil y documentación incompleta.
- Usar `jsonify` directo → respuestas inconsistentes con el frontend.
- No invalidar cache después de escribir → el frontend ve datos viejos.
- Hardcodear dominios/cookies → usa variables de entorno y `config.py`.
- Subir archivos sin `file_storage` → rutas mal guardadas; usar helpers y `UPLOAD_FOLDER`.
- En pruebas, usar la BD real por accidente → usa config `testing` (SQLite) y `JWT_TOKEN_LOCATION=['headers']`.

---

## 8) Recomendaciones finales para ADSO
- Versionado: ramas pequeñas por feature, commits claros. `git status` frecuente.
- Documenta: agrega notas en `docs/` o un README corto por feature; asegura que `/api/v1/docs/schema` se mantenga coherente.
- Colaboración: acordar contratos de respuesta con frontend (estructura `success/data/meta`, enums); usar Swagger para validar.
- Seguridad: mantener JWT seguro en prod (`JWT_COOKIE_SECURE=True`, `SameSite=None`, dominios correctos); CORS ajustado a orígenes válidos.
- Rendimiento: usa filtros/orden/paginación del factory; evita relaciones pesadas si no se necesitan (`include_relations=false` por defecto).
- Pruebas rápidas antes de entregar: `pytest -q`, `python scripts/smoke_backend.py`, `python scripts/test_swagger.py`.
- Aprendizaje continuo: lee `app/utils/namespace_helpers.py` (CRUD autogenerado) y `app/models/animals.py` (modelo completo con enums, relaciones y validaciones) como referencia.

---

## 9) Mini chuleta de comandos útiles
- Levantar en dev: `python run.py` (HTTPS adhoc si `USE_HTTPS=true`).
- Migrar: `flask db migrate -m "msg"` + `flask db upgrade`.
- Pruebas: `pytest -q`.
- Smoke docs: `python scripts/test_swagger.py`.
- Seguridad básica: `python scripts/verify_security_basic.py`.
