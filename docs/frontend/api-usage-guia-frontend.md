# Guia de uso del Frontend con la API (Finca)

Esta guia explica como consumir la API desde el frontend, autenticarse y probar endpoints con Swagger UI.

## Endpoints clave

- Base API: `https://finca.isladigital.xyz/api/v1/`
- Swagger UI: `https://finca.isladigital.xyz/api/v1/docs/`
- Esquema OpenAPI (JSON): `https://finca.isladigital.xyz/api/v1/swagger.json`

## Autenticacion y seguridad

La API usa JWT en cookies y proteccion CSRF.

- Tras el login, el servidor devuelve cookies con el `access_token`.
- Para metodos POST/PUT/PATCH/DELETE, añade el header `X-CSRF-TOKEN` con el valor de la cookie `csrf_access_token`.
- En fetch usa `credentials: 'include'` para enviar cookies.

## Probar con Swagger UI

- Abre `https://finca.isladigital.xyz/api/v1/docs/`.
- Pulsa "Authorize" si necesitas Bearer; con cookies puedes probar directamente.
- La UI intenta añadir `X-CSRF-TOKEN` leyendo la cookie `csrf_access_token`.

## Ejemplos rapidos

### GET (listado)

```javascript
async function fetchAnimals() {
  const res = await fetch('https://finca.isladigital.xyz/api/v1/animals', {
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
  const res = await fetch('https://finca.isladigital.xyz/api/v1/animals', {
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
- `POST /api/v1/auth/recover` (publico): `{ "email": "" }` o `{ "identification": "" }`. Devuelve `reset_token`, `expires_in` y `email_hint`.
- `POST /api/v1/auth/reset-password`: `{ "reset_token": "", "new_password": "" }`. Responde `should_clear_auth=true`.

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
