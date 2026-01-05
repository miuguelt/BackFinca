# Guia de uso del Frontend con la API (Finca)

Esta guia explica como consumir la API desde el frontend, autenticarse y probar endpoints con Swagger UI.

## Endpoints clave

- Base API: `https://finca.enlinea.sbs/api/v1/`
- Swagger UI: `https://finca.enlinea.sbs/api/v1/docs/`
- Esquema OpenAPI (JSON): `https://finca.enlinea.sbs/api/v1/swagger.json`

## Troubleshooting: 503 "no available server" (no es CORS)

Si el frontend falla con `503 no available server`, el error viene del servidor (proxy/ingress) y **no** de CORS.

Puedes confirmarlo directo en el navegador o con `curl`:

- `https://finca.enlinea.sbs/api/v1/health` → si responde `503`, no hay backend disponible.
- Incluso el root `https://villaluz.enlinea.sbs` → `503` indica caída/ruta no disponible (Traefik/Coolify/servicio caído o no enrutable desde tu red/VPN).

### Qué hacer para poder probar login

- **Backend local**: en tu `.env` pon `VITE_PROXY_TARGET=http://127.0.0.1:8081` (o el puerto real del backend), levanta el backend en ese puerto y reinicia `npm run dev`.
- **Backend remoto**: hay que levantar/arreglar el backend/ingress (Coolify/Traefik) hasta que `.../api/v1/health` responda `200`; cuando eso ocurra, el login debería funcionar.

## Autenticacion y seguridad

La API usa JWT en cookies y proteccion CSRF.

- Tras el login, el servidor devuelve cookies con el `access_token`.
- Para metodos POST/PUT/PATCH/DELETE, añade el header `X-CSRF-TOKEN` con el valor de la cookie `csrf_access_token`.
- En fetch usa `credentials: 'include'` para enviar cookies.

## Probar con Swagger UI

- Abre `https://finca.enlinea.sbs/api/v1/docs/`.
- Pulsa "Authorize" si necesitas Bearer; con cookies puedes probar directamente.
- La UI intenta añadir `X-CSRF-TOKEN` leyendo la cookie `csrf_access_token`.

## Ejemplos rapidos

### GET (listado)

```javascript
async function fetchAnimals() {
  const res = await fetch('https://finca.enlinea.sbs/api/v1/animals', {
    method: 'GET',
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Error obteniendo animales');
  return res.json();
}
```

### POST (crear) con CSRF

```javascript
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

async function createAnimal(payload) {
  const csrf = getCookie('csrf_access_token');
  const res = await fetch('https://finca.enlinea.sbs/api/v1/animals', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-TOKEN': csrf || '',
    },
    body: JSON.stringify(payload),
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Error creando animal');
  return res.json();
}
```

## Buenas practicas

- No expongas secretos en el frontend.
- Valida respuestas y maneja errores (401/403 -> autenticacion/CSRF).
- Usa dominios y cookies correctos en produccion.

## Recuperacion y cambio de contrasena

Flujo soportado por los nuevos endpoints de auth:

- `POST /api/v1/auth/change-password` (requiere JWT): `{ "current_password": "", "new_password": "" }`. Responde `should_clear_auth=true` para forzar re-login.
- `POST /api/v1/auth/recover` (publico): `{ "identifier": "" }` o `{ "email": "" }` o `{ "identification": "" }`. Devuelve `reset_token`, `expires_in` y `email_hint`.
- `POST /api/v1/auth/reset-password`: `{ "reset_token": "", "new_password": "" }`. Responde `should_clear_auth=true`.

Notas del backend:

- `identifier` acepta email o numero de identificacion (string o number).
- `reset_token` es un token JWT temporal con proposito `password_reset`.
- Validaciones: `new_password` debe cumplir las reglas de complejidad; el backend rechaza si es igual a la actual.
- Errores comunes: `404` usuario no existe, `403` usuario inactivo, `401` token invalido/expirado, `422` validacion.
- Rate limit por IP en recover/reset (ver configuracion `RATE_LIMIT_CONFIG`).

## Casos de uso en el frontend (ejemplos)

### Login con formulario (manejo de errores y cookies)

```javascript
async function loginWithForm({ identifier, password }) {
  const res = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ identifier, password }),
  });
  const data = await res.json();
  if (!res.ok) {
    const message = data.message || 'Credenciales invalidas';
    throw new Error(message);
  }
  return data.data?.user || data.user;
}
```

### Mostrar errores en formulario (login)

```javascript
async function handleLoginSubmit(form, setError, setLoading) {
  setLoading(true);
  setError('');
  try {
    const identifier = form.identifier.value.trim();
    const password = form.password.value;
    await loginWithForm({ identifier, password });
    // redirigir a dashboard
  } catch (err) {
    setError(err.message || 'No se pudo iniciar sesion');
  } finally {
    setLoading(false);
  }
}
```

### Request con CSRF (utilidad reutilizable)

```javascript
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

async function apiFetch(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const headers = { ...(options.headers || {}) };
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    headers['X-CSRF-TOKEN'] = getCookie('csrf_access_token') || '';
  }
  const res = await fetch(url, {
    credentials: 'include',
    ...options,
    headers,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.message || 'Error en la solicitud');
  }
  return data;
}
```

### Proteccion de rutas (verificar sesion)

```javascript
async function getCurrentUser() {
  const res = await fetch('/api/v1/auth/me', {
    method: 'GET',
    credentials: 'include',
  });
  if (res.status === 401) return null;
  const data = await res.json();
  if (!res.ok) return null;
  return data.data?.user || data.user;
}
```

### Cache simple en memoria (listado de animales)

```javascript
const animalsCache = { value: null, ts: 0 };
const CACHE_TTL_MS = 30 * 1000;

async function fetchAnimalsCached() {
  const now = Date.now();
  if (animalsCache.value && now - animalsCache.ts < CACHE_TTL_MS) {
    return animalsCache.value;
  }
  const data = await apiFetch('/api/v1/animals', { method: 'GET' });
  animalsCache.value = data;
  animalsCache.ts = now;
  return data;
}
```

### Logout y limpieza local

```javascript
async function logout() {
  try {
    await apiFetch('/api/v1/auth/logout', { method: 'POST' });
  } catch (err) {
    // ignorar error de red, igual limpiar estado local
  }
  // limpiar estado local y redirigir a login
}
```

### Ejemplo rapido: cambio de contrasena (Bearer en headers)

```javascript
async function changePassword(currentPassword, newPassword, accessToken) {
  const res = await fetch('/api/v1/auth/change-password', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    credentials: 'include',
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.message || 'Error al cambiar contrasena');
  if (data.data?.should_clear_auth) {
    // Limpia tokens/cookies y redirige a login
  }
  return data;
}
```

### Ejemplo rapido: recuperacion y restablecimiento

```javascript
async function requestReset(identifier) {
  const res = await fetch('/api/v1/auth/recover', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: identifier }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.message);
  return data.data.reset_token; // guardar temporalmente
}

async function resetPassword(resetToken, newPassword) {
  const res = await fetch('/api/v1/auth/reset-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reset_token: resetToken, new_password: newPassword }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.message);
  if (data.data?.should_clear_auth) {
    // obligar a login manual tras el cambio
  }
  return data;
}
```

Recomendaciones:

- Muestra mensajes genericos de exito/error para no revelar si un email existe.
- El token de recuperacion es de uso unico; descartalo tras aplicarlo.
- Tras restablecer la contrasena, limpia cualquier estado de sesion previo.

---

Amplia esta guia con casos especificos de tu frontend (formularios, login, cache, etc.).

## Recomendacion para escalar: feed de actividad (backend)

Para evitar reconstruir el feed en el frontend y soportar auditoria/notificaciones, se recomienda un endpoint paginado que devuelva eventos normalizados.

### Propuesta de endpoint

- `GET /api/v1/activity` (opcional: `GET /api/v1/users/{id}/activity`)
- Filtros: `entity`, `action`, `from`, `to`, `severity`, `user_id`, `animal_id`, `page`, `per_page`
- Orden: `created_at DESC`

### Respuesta sugerida (normalizada)

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "evt_123",
        "action": "update",
        "entity": "animal",
        "entity_id": 45,
        "title": "Animal actualizado",
        "description": "Peso actualizado a 320kg",
        "severity": "info",
        "created_at": "2026-01-04T22:25:06Z",
        "actor": { "id": 9, "fullname": "Juan Perez" },
        "relations": { "animal_id": 45 }
      }
    ],
    "page": 1,
    "per_page": 20,
    "total": 143
  }
}
```

### Campos recomendados

- `action`: `create|update|delete|alert|system`
- `severity`: `info|warning|critical`
- `relations`: ids relacionados (`animal_id`, `user_id`, etc.) para deep links.
- `actor`: informacion minima del usuario que origina el evento.

## Instrucciones para el frontend (actividad)

### Reglas de consumo

- Renderiza `items` en orden descendente por `created_at`.
- Usa filtros desde la UI sin transformar la data.
- Maneja estados `loading`, `empty`, `error`.
- Cache en memoria opcional por combinacion de filtros.

### Ejemplo de fetch con filtros

```javascript
async function fetchActivity({ page = 1, perPage = 20, entity, action, from, to, severity } = {}) {
  const params = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
  });
  if (entity) params.set('entity', entity);
  if (action) params.set('action', action);
  if (from) params.set('from', from);
  if (to) params.set('to', to);
  if (severity) params.set('severity', severity);

  const res = await fetch(`/api/v1/activity?${params.toString()}`, {
    method: 'GET',
    credentials: 'include',
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.message || 'Error cargando actividad');
  return data.data;
}
```

### Ejemplo de paginado simple

```javascript
async function loadNextPage(state, setState) {
  if (state.loading || !state.hasMore) return;
  setState({ ...state, loading: true });
  try {
    const data = await fetchActivity({ page: state.page + 1, perPage: state.perPage });
    const items = [...state.items, ...(data.items || [])];
    const total = data.total || items.length;
    const hasMore = items.length < total;
    setState({ ...state, items, page: data.page, total, hasMore, loading: false });
  } catch (err) {
    setState({ ...state, loading: false, error: err.message || 'Error cargando actividad' });
  }
}
```
