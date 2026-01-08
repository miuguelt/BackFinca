# Guía Frontend (API) - Finca Villaluz

Esta guía se sirve en `GET /api/v1/docs/guia-frontend` y resume lo necesario para consumir la API desde el frontend.

Guía extendida (repositorio): `docs/frontend/api-usage-guide-frontend.md`.

## Endpoints clave

- Base API: `/api/v1/`
- Swagger UI: `/api/v1/docs/`
- OpenAPI JSON: `/api/v1/swagger.json`

## Autenticación (cookies + CSRF)

- En `fetch`: usa `credentials: 'include'`.
- Para `POST/PUT/PATCH/DELETE`: envía `X-CSRF-TOKEN` con el valor de la cookie `csrf_access_token`.

## Actividad y analítica (perfil "Tu actividad")

- Timeline global: `GET /api/v1/activity`
- Timeline del usuario autenticado: `GET /api/v1/activity/me`
- Resumen 7d+30d (tarjetas + agregados): `GET /api/v1/activity/me/summary`
- Agregados del usuario (gráficas): `GET /api/v1/activity/me/stats?days=30`
- Agregados globales (o por filtros): `GET /api/v1/activity/stats?days=30`
- Valores para filtros (dropdowns): `GET /api/v1/activity/filters?days=365`

Filtros soportados en timeline/stats:

- `entity`, `action`, `severity`, `entity_id`, `user_id` (solo `/activity`), `animal_id`, `from`, `to`

## Performance (frontend)

### ETag / 304 (recomendado)

Los endpoints de lectura con caché (p.ej. `/activity/me/summary`, `/activity/*/stats`, `/activity/filters`) devuelven `ETag`.

- Si el frontend reconsulta y envía `If-None-Match: <etag>`, el backend puede responder `304 Not Modified` (sin body).

### Paginación por cursor (timeline)

Para feeds grandes, usa keyset pagination:

- Request: `GET /api/v1/activity/me?cursor=<cursor>&limit=20`
- Response: `data.next_cursor` y `data.has_more`

### Payload mínimo (timeline)

Para reducir payload:

- `include=actor,relations` (por defecto incluye ambos; si envías `include=actor` omite `relations`)
- `fields=id,entity,action,created_at,title` (devuelve solo esos campos)

### Filtros

`GET /api/v1/activity/filters?days=365&scope=me` (default) devuelve solo valores presentes en tu actividad.
