# Guía de uso del Frontend con la API (Finca)

Esta guía explica cómo consumir la API desde el frontend, autenticarse, y probar endpoints con Swagger UI.

## Endpoints clave

- Base API: `https://finca.isladigital.xyz/api/v1/`
- Swagger UI: `https://finca.isladigital.xyz/api/v1/docs/`
- Esquema OpenAPI (JSON): `https://finca.isladigital.xyz/api/v1/swagger.json`

## Autenticación y seguridad

La API usa JWT en cookies y protección CSRF.

- Tras el login, el servidor devuelve cookies con el `access_token`.
- Para métodos POST/PUT/PATCH/DELETE, añade el header `X-CSRF-TOKEN` con el valor de la cookie `csrf_access_token`.
- En fetch usa `credentials: 'include'` para enviar cookies.

## Probar con Swagger UI

- Abre `https://finca.isladigital.xyz/api/v1/docs/`.
- Pulsa "Authorize" si necesitas Bearer; con cookies puedes probar directamente.
- La UI intenta añadir `X-CSRF-TOKEN` leyendo la cookie `csrf_access_token`.

## Ejemplos rápidos

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

## Buenas prácticas

- No expongas secretos en el frontend.
- Valida respuestas y maneja errores (401/403 -> autenticación/CSRF).
- Usa dominios y cookies correctos en producción.

---

Amplía esta guía con casos específicos de tu frontend (formularios, login, cache, etc.).