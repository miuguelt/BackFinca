# Guia Frontend (API) - Finca Villaluz

Esta guia se sirve en `GET /api/v1/docs/guia-frontend` y su version HTML en `GET /api/v1/docs/guia-frontend-html`.
Guia extendida (repositorio): `docs/frontend/api-usage-guide-frontend.md`.

## Checklist rapido para pruebas (10-15 min)

1. Abre `GET /api/v1/health` y confirma `200`.
2. Define la base URL de tu frontend (ver "Base URL y entornos").
3. Inicia sesion con `POST /api/v1/auth/login`.
4. Asegura cookies en el navegador (`credentials: 'include'`).
5. Para mutaciones, envia `X-CSRF-TOKEN` con el valor de la cookie `csrf_access_token`.
6. Prueba `GET /api/v1/auth/me` y un listado (`/animals`, `/fields`, etc.).
7. Verifica logout (`POST /api/v1/auth/logout`) y reintento de login.

> Si ves `503 no available server`, el problema es del backend/ingress (no de CORS).

## Diagramas rapidos

![Auth flow (cookies + CSRF)](/static/docs/guia-frontend-auth-flow.svg)

![Flujo de pruebas frontend](/static/docs/guia-frontend-test-flow.svg)

## Endpoints clave

- Base API: `/api/v1/`
- Swagger UI: `/api/v1/docs/`
- OpenAPI JSON: `/api/v1/swagger.json`
- Esquema de modelos: `/api/v1/docs/schema`
- Ejemplos JSON: `/api/v1/docs/examples`
- Health check: `/api/v1/health`

## Base URL y entornos

| Entorno | Base URL | Uso |
| --- | --- | --- |
| Produccion | `https://finca.enlinea.sbs/api/v1` | Frontend real |
| Local | `http://127.0.0.1:8081/api/v1` | Backend local (ajusta el puerto) |

Notas:

- En desarrollo, puedes usar un proxy del dev server para evitar CORS.
- Si usas Vite, una opcion comun es `VITE_PROXY_TARGET=http://127.0.0.1:8081` y `VITE_API_BASE_URL=/api/v1`.
- Si haces llamadas directas al backend, agrega tu origen a `CORS_ORIGINS` en el `.env` del backend (ej: `http://localhost:5173`).

## Autenticacion con cookies + CSRF (recomendada en navegador)

La API usa JWT en cookies HttpOnly y proteccion CSRF.

### 1) Login

`POST /api/v1/auth/login`

Body JSON:

```json
{
  "identifier": "99999999",
  "password": "password123"
}
```

Notas:

- `identifier` acepta email o numero de identificacion.
- En entornos de demo puede existir el usuario admin anterior; cambia estas credenciales en produccion.

### 2) Enviar cookies en cada request

En el frontend usa `credentials: 'include'` para que el navegador envie cookies.

### 3) Enviar CSRF en metodos de escritura

Para `POST/PUT/PATCH/DELETE`, agrega `X-CSRF-TOKEN` con el valor de la cookie `csrf_access_token`.

### 4) Helper base para requests con Refresh Token

El backend devuelve detalles en el error 401 para indicar si se debe intentar un refresh.

```javascript
/* 
 Estructura del error 401 desde el backend:
 {
   "success": false,
   "error": {
     "code": "TOKEN_EXPIRED",
     "details": {
       "client_action": "ATTEMPT_REFRESH" // o "CLEAR_AUTH_AND_RELOGIN"
     }
   }
 }
*/

const API_BASE_URL = '/api/v1';
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) prom.reject(error);
    else prom.resolve(token);
  });
  failedQueue = [];
};

async function apiFetch(path, options = {}) {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Content-Type': 'application/json',
    },
    credentials: 'include'
  });

  // Manejo de 401 con lógica de refresh backend-driven
  if (response.status === 401) {
    const data = await response.json().catch(() => ({}));
    
    // Si el backend sugiere refrescar y no es un reintento
    const shouldRefresh = data.error?.details?.client_action === 'ATTEMPT_REFRESH';
    
    if (shouldRefresh && !options._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(() => {
          return apiFetch(path, { ...options, _retry: true });
        }).catch(err => Promise.reject(err));
      }

      options._retry = true;
      isRefreshing = true;

      try {
        const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include'
        });

        if (!refreshRes.ok) throw new Error('Refresh failed');
        
        processQueue(null, true);
        isRefreshing = false;
        return apiFetch(path, options);
      } catch (err) {
        processQueue(err, null);
        isRefreshing = false;
        // Si falla el refresh, redirigir a login
        window.location.href = '/login';
        return Promise.reject(err);
      }
    }
    
    // Si no es para refrescar (ej: token revocado o refresh expirado), lanzar error
    throw new Error(data.message || 'Sesión expirada');
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.message || 'Error en la solicitud');
  return data;
}
```

### 5) Verificar sesion

```javascript
async function getCurrentUser() {
  const res = await apiFetch('/auth/me', { method: 'GET' });
  return res.data?.user || res.user;
}
```

## Autenticacion Bearer (opcional)

Para scripts o integraciones fuera del navegador, puedes usar `Authorization: Bearer <token>`.

```javascript
const res = await fetch(`${API_BASE_URL}/auth/me`, {
  headers: { Authorization: `Bearer ${token}` },
});
```

## Probar con Swagger UI

1. Abre `/api/v1/docs/`.
2. Ejecuta `POST /auth/login` para obtener cookies.
3. Prueba endpoints con `Try it out`.
4. Si ves 401/403, revisa cookies y CSRF.

## Estructura de respuestas

Exito:

```json
{
  "success": true,
  "message": "OK",
  "data": {
    "...": "..."
  }
}
```

Error:

```json
{
  "success": false,
  "error": "BadRequest",
  "message": "Detalle del error",
  "details": {}
}
```

## Actividad y analitica (perfil "Tu actividad")

- Timeline global: `GET /api/v1/activity`
- Timeline del usuario autenticado: `GET /api/v1/activity/me`
- Resumen 7d+30d (tarjetas + agregados): `GET /api/v1/activity/me/summary`
- Agregados del usuario (graficas): `GET /api/v1/activity/me/stats?days=30`
- Agregados globales (o por filtros): `GET /api/v1/activity/stats?days=30`
- Valores para filtros (dropdowns): `GET /api/v1/activity/filters?days=365`

Filtros soportados en timeline/stats:

- `entity`, `action`, `severity`, `entity_id`, `user_id` (solo `/activity`), `animal_id`, `from`, `to`

## Paginacion, filtros y performance

### ETag / 304

Los endpoints de lectura con cache (ej: `/activity/me/summary`, `/activity/*/stats`, `/activity/filters`) devuelven `ETag`.

- Si reconsultas y envias `If-None-Match: <etag>`, el backend puede responder `304 Not Modified`.

### Paginacion por cursor (timeline)

- Request: `GET /api/v1/activity/me?cursor=<cursor>&limit=20`
- Response: `data.next_cursor` y `data.has_more`

### Payload minimo (timeline)

- `include=actor,relations` (default incluye ambos; `include=actor` omite `relations`)
- `fields=id,entity,action,created_at,title`

### Filtros (dropdowns)

`GET /api/v1/activity/filters?days=365&scope=me` devuelve valores presentes en tu actividad.

## Casos de prueba recomendados

1. Login correcto e incorrecto (valida mensajes).
2. `GET /auth/me` sin sesion (espera 401).
3. Listado con filtros y paginacion (ej. animales).
4. Crear/editar/eliminar un recurso (verifica CSRF).
5. Logout y limpieza de estado local.

## Imagenes y archivos (si aplica)

- Usa siempre el campo `url` entregado por el backend (no construyas URLs a mano).
- En el repositorio hay guias adicionales:
  - `docs/frontend/ANIMAL_IMAGES_USAGE.md`
  - `docs/frontend/SOLUCION_IMAGENES_FRONTEND.md`

## Troubleshooting rapido

- `401`: sesion expirada o sin cookies.
- `403`: CSRF invalido o ausente.
- `415`: falta `Content-Type: application/json`.
- `422`: validacion de campos.
- `503`: backend o proxy caido.
- CORS: agrega tu origen a `CORS_ORIGINS` en el backend.

## Checklist final de integracion

- Base URL correcta en el frontend.
- Cookies habilitadas y `credentials: 'include'`.
- CSRF enviado en mutaciones.
- Manejo de errores y estados vacios.
- Cache ETag / paginacion donde aplique.
