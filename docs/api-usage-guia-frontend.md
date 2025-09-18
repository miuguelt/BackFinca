# Guía de uso del API para Frontend

Esta guía resume cómo consumir los endpoints del API desde el frontend. Se aplica a todos los namespaces CRUD generados por el factory y a los endpoints personalizados de Vacunas.

## Parámetros estándar (listas)
- page: número de página (>=1). Por defecto 1.
- limit: tamaño de página (>=1). Por defecto 50.
- search: texto de búsqueda simple sobre campos configurados como _searchable_fields.
- sort_by: campo permitido en _sortable_fields (ej: id, name, created_at).
- sort_order: asc o desc. Por defecto asc.
- include_relations: true para incluir relaciones configuradas en el modelo (puede impactar el rendimiento si hay relaciones profundas).
- fields: lista separada por comas para proyectar columnas del item (ej: id,name,status). Afecta tanto a lista como a detalle.
- export: si vale csv, devuelve CSV del listado (ignora paginación salvo que se envíen page/limit explícitos).
- Filtros por campo: cada campo en _filterable_fields se puede pasar como ?campo=valor o ?campo=v1,v2 (OR simple por valores).

## Parámetros estándar (detalle)
- include_relations: true para incluir relaciones en el objeto detalle.
- fields: proyección de campos del objeto, igual que en el listado.

## Estructura de respuesta
- Éxito (lista): { success, message, data: { items: [...], page, limit, total_items } }
- Éxito (detalle): { success, message, data: { ...objeto... } }
- Error: { success: false, error, message, details? }

Cabeceras útiles: ETag con metadatos del listado cuando corresponde.

## Ejemplos (listas)
- Paginación: GET /api/v1/animals?page=2&limit=20
- Búsqueda: GET /api/v1/vaccines?search=anti
- Orden: GET /api/v1/vaccines?sort_by=created_at&sort_order=desc
- Filtros: GET /api/v1/vaccines?type=PREVENTIVA&route_administration_id=1,2
- Proyección: GET /api/v1/vaccines?fields=id,name,manufacturer
- Relaciones: GET /api/v1/animals?include_relations=true
- Export CSV: GET /api/v1/vaccines?export=csv

## Ejemplos (detalle)
- GET /api/v1/vaccines/10?fields=id,name,type
- GET /api/v1/animals/5?include_relations=true

## Avanzado: filtros con operadores (próximamente)
Estos ejemplos reflejan la sintaxis prevista una vez se añada soporte a operadores (lt/gt/in) en el factory. Aún no están activos en el backend actual.

- Menor que (lt) por fecha creada:
  - GET /api/v1/vaccines?created_at__lt=2025-01-01
- Mayor que (gt) por fecha creada:
  - GET /api/v1/vaccines?created_at__gt=2024-01-01
- En lista (in) por IDs:
  - GET /api/v1/animals?id__in=1,2,5,9
- Rango numérico (gt/lt) por peso:
  - GET /api/v1/animals?weight__gt=200&weight__lt=400
- Rango de fechas (gte/lte):
  - GET /api/v1/vaccinations?date__gte=2024-01-01&date__lte=2024-12-31

Cuando el soporte esté disponible, los operadores válidos esperados serán: __lt, __lte, __gt, __gte, __in, __ne.

## Snippets por modelo (ejemplos rápidos)
A continuación algunos ejemplos prácticos por modelo común. Consulta /api/v1/docs/schema para conocer los campos exactos, requeridos y enums.

### Animals
- Listar con filtros y proyección:
  - GET /api/v1/animals?search=cow&fields=id,name,species_id&sort_by=created_at&sort_order=desc&page=1&limit=20
- Detalle (solo campos clave):
  - GET /api/v1/animals/5?fields=id,name,status
- Crear (estructura típica, valores ilustrativos):
```
POST /api/v1/animals/
Content-Type: application/json
{
  "name": "Vaca 101",
  "species_id": 1,
  "breed_id": 2,
  "birth_date": "2022-05-10",
  "status": "ACTIVE"
}
```

### Users
- Listado paginado y ordenado:
  - GET /api/v1/users?fields=id,username,role&sort_by=created_at&sort_order=desc&page=1&limit=10
- Detalle con campos mínimos:
  - GET /api/v1/users/3?fields=id,username,role

### Vaccines
- Búsqueda y filtros básicos:
  - GET /api/v1/vaccines?search=anti&route_administration_id=1,2&fields=id,name,type
- Detalle:
  - GET /api/v1/vaccines/10?fields=id,name,type,route_administration_id
- Endpoints personalizados útiles:
  - GET /api/v1/vaccines/with-route-administration
  - GET /api/v1/vaccines/with-route-administration/stats
  - GET /api/v1/vaccines/with-route-administration/by-route/1

## Buenas prácticas en frontend
- Siempre limita y pagina; evita pedir listas sin paginación.
- Usa fields para reducir el tamaño de las respuestas.
- Activa include_relations solo cuando sea estrictamente necesario.
- Para listados con filtros dinámicos, construye la query con los nombres en _filterable_fields.
- Reintenta llamadas fallidas (backoff) solo en errores 5xx; no reintentes 4xx.
- Cachea resultados de listas con el par (querystring) como clave; invalida con cambios de filtros o con cache_bust=1 si es necesario.

## Notas de rendimiento
- Las respuestas de lista pueden cachearse de forma ligera por clave de consulta.
- El servidor puede devolver ETag; úsalo para condicionales si necesitas optimizar aún más.
- La proyección de campos y el no incluir relaciones por defecto están orientados a minimizar latencia.

## Recursos
- Swagger UI: /api/v1/docs/
- Esquema dinámico: /api/v1/docs/schema
- Ejemplos: /api/v1/docs/examples
- Esta guía (Markdown): /api/v1/docs/guia-frontend