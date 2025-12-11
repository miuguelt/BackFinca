# Guía de Optimización PWA - Backend API

## 📋 Resumen

El backend ahora está optimizado para aplicaciones PWA (Progressive Web Apps) con soporte completo para:

✅ Caché HTTP inteligente con ETags y Last-Modified
✅ Respuestas 304 Not Modified para reducir transferencia de datos
✅ Sincronización delta (incremental) con `?since=timestamp`
✅ Endpoint `/metadata` para revalidación ligera
✅ Headers de estrategia de caché para Service Workers
✅ Caché segmentada por usuario (datos privados)
✅ Configuración diferenciada por tipo de dato

---

## 🎯 Headers HTTP de Respuesta

### Headers Estándar de Caché

Todas las respuestas de listado incluyen:

```http
Cache-Control: private, max-age=120, stale-while-revalidate=60
ETag: "42-2025-09-06T12:00:00Z"
Last-Modified: Sat, 06 Sep 2025 12:00:00 GMT
X-API-Version: 1.0.0
X-Cache-Strategy: stale-while-revalidate
```

### Headers Específicos de Paginación

```http
X-Total-Count: 156
X-Has-More: true
Vary: Authorization, Cookie
```

---

## 🔄 Validación Condicional (304 Not Modified)

### Usar ETag para verificar cambios

**Request:**
```http
GET /api/v1/users
If-None-Match: "42-2025-09-06T12:00:00Z"
```

**Response (sin cambios):**
```http
HTTP/1.1 304 Not Modified
ETag: "42-2025-09-06T12:00:00Z"
Cache-Control: private, max-age=120, stale-while-revalidate=60
```

**Response (con cambios):**
```http
HTTP/1.1 200 OK
ETag: "45-2025-09-07T14:30:00Z"
Content-Type: application/json

{
  "success": true,
  "data": [...]
}
```

### Usar Last-Modified para verificar cambios

**Request:**
```http
GET /api/v1/diseases
If-Modified-Since: Sat, 06 Sep 2025 12:00:00 GMT
```

**Response (sin cambios):**
```http
HTTP/1.1 304 Not Modified
Last-Modified: Sat, 06 Sep 2025 12:00:00 GMT
```

---

## 📡 Sincronización Delta (Incremental)

### Obtener solo registros modificados desde una fecha

**Request:**
```http
GET /api/v1/users?since=2025-09-06T12:00:00Z
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 43,
      "identification": 1757180418,
      "fullname": "Juan Pérez Final",
      "updated_at": "2025-09-06T17:40:19Z"
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "limit": 50,
      "total_items": 1,
      "total_pages": 1
    }
  }
}
```

**Uso típico en PWA:**

```typescript
// 1. Obtener timestamp de última sincronización
const lastSync = localStorage.getItem('users_last_sync');

// 2. Solicitar solo cambios recientes
const response = await fetch(
  `${API_URL}/users?since=${lastSync}`,
  { headers: { 'Authorization': `Bearer ${token}` } }
);

// 3. Actualizar timestamp de sincronización
localStorage.setItem('users_last_sync', new Date().toISOString());
```

---

## 🔍 Endpoint de Metadata Ligero

### Verificar si hay cambios sin descargar datos

**Request:**
```http
GET /api/v1/users/metadata
```

**Response:**
```json
{
  "success": true,
  "data": {
    "resource": "users",
    "total_count": 51,
    "last_modified": "2025-09-07T14:58:50Z",
    "etag": "51-2025-09-07T14:58:50Z"
  }
}
```

**Uso típico:**

```typescript
// Verificar si hay cambios antes de descargar lista completa
const metadata = await fetch(`${API_URL}/users/metadata`);
const { etag } = await metadata.json();

if (etag !== cachedEtag) {
  // Hay cambios, descargar lista actualizada
  const users = await fetch(`${API_URL}/users`);
}
```

---

## ⚙️ Configuración de Caché por Tipo de Dato

### Datos Maestros (públicos, cambian poco)

**Modelos:** Diseases, Breeds, Species, Medications, Vaccines

```
Cache-Control: public, max-age=1800, stale-while-revalidate=600
X-Cache-Strategy: cache-first
```

**Recomendación Service Worker:**
- Estrategia: **Cache First**
- TTL: 30 minutos
- Revalidar en background cada 10 minutos

### Datos Transaccionales (privados, cambian frecuentemente)

**Modelos:** Vaccinations, Treatments, AnimalDiseases

```
Cache-Control: private, max-age=120, stale-while-revalidate=60
X-Cache-Strategy: stale-while-revalidate
```

**Recomendación Service Worker:**
- Estrategia: **Stale While Revalidate**
- TTL: 2 minutos
- Mostrar caché mientras se revalida

### Datos de Usuario (privados, críticos)

**Modelos:** User

```
Cache-Control: private, max-age=60, stale-while-revalidate=30
X-Cache-Strategy: network-first
```

**Recomendación Service Worker:**
- Estrategia: **Network First**
- TTL: 1 minuto
- Solo usar caché si offline

---

## 🎨 Ejemplo de Service Worker

```javascript
// Detectar estrategia de caché del header X-Cache-Strategy
self.addEventListener('fetch', (event) => {
  const request = event.request;

  event.respondWith(
    fetch(request.clone())
      .then(response => {
        const strategy = response.headers.get('X-Cache-Strategy');
        const cacheControl = response.headers.get('Cache-Control');

        switch (strategy) {
          case 'cache-first':
            return cacheFirstStrategy(request, response);

          case 'network-first':
            return networkFirstStrategy(request, response);

          case 'stale-while-revalidate':
          default:
            return staleWhileRevalidateStrategy(request, response);
        }
      })
      .catch(() => caches.match(request))
  );
});

async function staleWhileRevalidateStrategy(request, response) {
  const cache = await caches.open('api-cache');

  // Guardar en caché
  cache.put(request, response.clone());

  // Retornar respuesta de red
  return response;
}

async function cacheFirstStrategy(request, response) {
  const cache = await caches.open('api-cache');
  const cached = await cache.match(request);

  if (cached) {
    // Revalidar en background
    fetch(request).then(res => cache.put(request, res));
    return cached;
  }

  cache.put(request, response.clone());
  return response;
}

async function networkFirstStrategy(request, response) {
  const cache = await caches.open('api-cache');
  cache.put(request, response.clone());
  return response;
}
```

---

## 📊 Ejemplo de Uso Completo en PWA

```typescript
class APIClient {
  private baseUrl = 'https://finca.isladigital.xyz/api/v1';
  private cachedETags = new Map<string, string>();

  async fetchUsers(options: {
    page?: number;
    limit?: number;
    since?: string;
  } = {}) {
    const params = new URLSearchParams();
    if (options.page) params.append('page', String(options.page));
    if (options.limit) params.append('limit', String(options.limit));
    if (options.since) params.append('since', options.since);

    const url = `${this.baseUrl}/users?${params}`;
    const cachedETag = this.cachedETags.get(url);

    const headers: HeadersInit = {
      'Authorization': `Bearer ${this.getToken()}`
    };

    // Agregar ETag si existe
    if (cachedETag) {
      headers['If-None-Match'] = cachedETag;
    }

    const response = await fetch(url, { headers });

    // 304 Not Modified - usar datos cacheados
    if (response.status === 304) {
      console.log('✅ Usando caché (304 Not Modified)');
      return this.getCachedData(url);
    }

    // 200 OK - datos nuevos
    const data = await response.json();

    // Guardar nuevo ETag
    const newETag = response.headers.get('ETag');
    if (newETag) {
      this.cachedETags.set(url, newETag);
    }

    // Guardar en IndexedDB para uso offline
    await this.saveToCache(url, data);

    return data;
  }

  async syncIncrementally(resource: string) {
    const lastSync = localStorage.getItem(`${resource}_last_sync`);
    const since = lastSync || new Date(0).toISOString();

    console.log(`🔄 Sincronizando ${resource} desde ${since}...`);

    const response = await fetch(
      `${this.baseUrl}/${resource}?since=${since}`,
      {
        headers: {
          'Authorization': `Bearer ${this.getToken()}`
        }
      }
    );

    const { data, meta } = await response.json();

    console.log(`✅ ${data.length} cambios descargados`);

    // Actualizar datos locales
    await this.mergeChanges(resource, data);

    // Actualizar timestamp
    localStorage.setItem(`${resource}_last_sync`, new Date().toISOString());

    return {
      changes: data.length,
      hasMore: meta.pagination.has_next_page
    };
  }
}
```

---

## 🚀 Mejores Prácticas

### 1. **Verificar cambios antes de descargar**

```typescript
// ❌ MAL: Descargar siempre
const users = await fetch('/api/v1/users');

// ✅ BIEN: Verificar primero
const metadata = await fetch('/api/v1/users/metadata');
const { etag } = await metadata.json();

if (etag !== cachedEtag) {
  const users = await fetch('/api/v1/users');
}
```

### 2. **Usar sincronización incremental**

```typescript
// ❌ MAL: Descargar todo cada vez
const all = await fetch('/api/v1/vaccinations');

// ✅ BIEN: Solo cambios recientes
const changes = await fetch(`/api/v1/vaccinations?since=${lastSync}`);
```

### 3. **Respetar headers de caché**

```typescript
// Leer estrategia del servidor
const strategy = response.headers.get('X-Cache-Strategy');
const maxAge = parseInt(
  response.headers.get('Cache-Control')
    ?.match(/max-age=(\d+)/)?.[1] || '0'
);

// Aplicar estrategia recomendada
if (strategy === 'cache-first') {
  // Usar caché agresivamente
} else if (strategy === 'network-first') {
  // Priorizar red
}
```

### 4. **Usar ETags para validación**

```typescript
// Siempre guardar ETags
const etag = response.headers.get('ETag');
if (etag) {
  localStorage.setItem(`${resource}_etag`, etag);
}

// Enviar en próxima petición
headers['If-None-Match'] = localStorage.getItem(`${resource}_etag`);
```

---

## 📝 Headers CORS Expuestos

El backend expone estos headers en respuestas CORS:

```
Access-Control-Expose-Headers:
  ETag,
  Last-Modified,
  Cache-Control,
  X-API-Version,
  X-Cache-Strategy,
  X-Has-More,
  X-Total-Count,
  Vary
```

---

## 🐛 Debugging

### Ver headers de caché en DevTools

```javascript
// En consola del navegador
fetch('/api/v1/users')
  .then(r => {
    console.log('ETag:', r.headers.get('ETag'));
    console.log('Cache-Control:', r.headers.get('Cache-Control'));
    console.log('Last-Modified:', r.headers.get('Last-Modified'));
    console.log('X-Cache-Strategy:', r.headers.get('X-Cache-Strategy'));
    return r.json();
  });
```

### Forzar recarga (bypass caché)

```http
GET /api/v1/users?cache_bust=1
```

---

## 📚 Referencias

- [HTTP Caching (MDN)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching)
- [Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [PWA Best Practices](https://web.dev/pwa/)
- [ETag Header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/ETag)
- [Cache-Control](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control)

---

**Última actualización:** 2025-10-05
**Versión API:** 1.0.0
