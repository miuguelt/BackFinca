# 🔧 Troubleshooting: Problemas Comunes del Frontend

## ✅ Buenas Noticias
El endpoint está funcionando correctamente. Las peticiones exitosas muestran:
```
✓ GET /api/v1/animal-images/58 → 200 OK (0 imágenes encontradas)
```

## ❌ Problema 1: URL Duplicada

**Error detectado en logs:**
```
❌ /api/v1/api/v1/animal-images/58 → 404 NOT FOUND
```

**Causa:** El frontend está concatenando la URL base que ya incluye `/api/v1` con el endpoint que también incluye `/api/v1`.

**Solución:**

### Opción A: Ajustar la configuración de API

```javascript
// ❌ INCORRECTO
const API_BASE = 'https://finca.isladigital.xyz/api/v1';
const endpoint = '/api/v1/animal-images/58';
const url = API_BASE + endpoint; // → /api/v1/api/v1/animal-images/58

// ✅ CORRECTO - Opción 1: Base incluye /api/v1, endpoint no
const API_BASE = 'https://finca.isladigital.xyz/api/v1';
const endpoint = '/animal-images/58';
const url = API_BASE + endpoint; // → /api/v1/animal-images/58

// ✅ CORRECTO - Opción 2: Base sin /api/v1, endpoint sí lo incluye
const API_BASE = 'https://finca.isladigital.xyz';
const endpoint = '/api/v1/animal-images/58';
const url = API_BASE + endpoint; // → /api/v1/animal-images/58
```

### Código a buscar en tu frontend:

Busca en tu código algo similar a esto y corrígelo:

```javascript
// Archivo: src/config/api.js o similar

// ❌ Si tienes esto:
export const API_BASE = 'https://finca.isladigital.xyz/api/v1';
export const ENDPOINTS = {
  getImages: (animalId) => `/api/v1/animal-images/${animalId}` // ← Quitar /api/v1
}

// ✅ Cámbialo por:
export const API_BASE = 'https://finca.isladigital.xyz/api/v1';
export const ENDPOINTS = {
  getImages: (animalId) => `/animal-images/${animalId}` // ← Sin /api/v1
}
```

---

## ❌ Problema 2: Campo `animal_id` no se envía

**Error detectado en logs:**
```
❌ POST /api/v1/animal-images/upload → 400 BAD REQUEST
Error: El campo animal_id es requerido
```

**Causa:** El `FormData` no está incluyendo el campo `animal_id` correctamente.

**Solución:**

### Verifica el código de upload:

```javascript
// ❌ INCORRECTO - animal_id no se añade o está mal
const formData = new FormData();
formData.append('files', file);
// Falta: formData.append('animal_id', animalId);

// ❌ INCORRECTO - animal_id está como undefined
const formData = new FormData();
formData.append('animal_id', undefined); // ← animal_id es undefined
formData.append('files', file);

// ✅ CORRECTO
const formData = new FormData();
formData.append('animal_id', animalId); // ← Asegúrate que animalId tiene valor
formData.append('files', file);

// Verificar antes de enviar
console.log('animal_id:', animalId); // ← Debe mostrar un número, no undefined
console.log('FormData entries:');
for (let pair of formData.entries()) {
  console.log(pair[0], pair[1]);
}
```

### Ejemplo completo de función de upload corregida:

```javascript
async function uploadAnimalImages(animalId, files) {
  // 1. Validar que animalId existe
  if (!animalId) {
    throw new Error('animalId es requerido');
  }

  // 2. Validar que hay archivos
  if (!files || files.length === 0) {
    throw new Error('Debe seleccionar al menos un archivo');
  }

  // 3. Crear FormData
  const formData = new FormData();

  // 4. Añadir animal_id como string o número
  formData.append('animal_id', animalId);

  // 5. Añadir archivos
  files.forEach(file => {
    formData.append('files', file);
  });

  // 6. Debug: Verificar contenido (QUITAR EN PRODUCCIÓN)
  console.log('=== Debug Upload ===');
  console.log('animal_id:', animalId);
  console.log('files count:', files.length);
  console.log('FormData entries:');
  for (let [key, value] of formData.entries()) {
    console.log(`  ${key}:`, value instanceof File ? value.name : value);
  }

  // 7. Obtener token
  const token = localStorage.getItem('token') || sessionStorage.getItem('token');
  if (!token) {
    throw new Error('No hay token de autenticación');
  }

  // 8. Enviar petición
  const response = await fetch('https://finca.isladigital.xyz/api/v1/animal-images/upload', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
      // NO incluir 'Content-Type' - el navegador lo establece automáticamente
    },
    body: formData
  });

  // 9. Verificar respuesta
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.message || 'Error al subir imágenes');
  }

  return await response.json();
}
```

---

## 🔍 Debugging en el Navegador

### 1. Verifica la petición en DevTools

**Chrome/Edge/Firefox:**
1. Abre DevTools (F12)
2. Ve a la pestaña "Network"
3. Filtra por "Fetch/XHR"
4. Haz la petición de upload
5. Busca la petición a `/animal-images/upload`
6. Click en la petición
7. Ve a la pestaña "Payload" o "Request"

**Deberías ver:**
```
animal_id: 58         ✅
files: (binary)       ✅
```

**Si ves:**
```
files: (binary)       ❌ Falta animal_id
```

Entonces el problema está en cómo construyes el FormData.

### 2. Verifica la URL de la petición

En la pestaña "Headers" de DevTools, busca:

```
✅ CORRECTO:
Request URL: https://finca.isladigital.xyz/api/v1/animal-images/upload

❌ INCORRECTO:
Request URL: https://finca.isladigital.xyz/api/v1/api/v1/animal-images/upload
```

---

## 📝 Checklist de Solución

Revisa estos puntos en tu código del frontend:

- [ ] **URL base correcta:** Sin duplicar `/api/v1`
  ```javascript
  // ✅ Correcto
  const API_BASE = 'https://finca.isladigital.xyz/api/v1';
  const url = `${API_BASE}/animal-images/upload`;
  ```

- [ ] **animalId tiene valor:** No es `undefined` o `null`
  ```javascript
  console.log('animalId:', animalId); // Debe mostrar un número
  ```

- [ ] **FormData incluye animal_id:**
  ```javascript
  formData.append('animal_id', animalId); // Antes de los archivos
  ```

- [ ] **FormData incluye archivos:**
  ```javascript
  files.forEach(file => formData.append('files', file));
  ```

- [ ] **Headers incluyen Authorization:**
  ```javascript
  headers: { 'Authorization': `Bearer ${token}` }
  ```

- [ ] **NO incluir Content-Type en headers:**
  ```javascript
  // ❌ NO hacer esto:
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'multipart/form-data' // ← QUITAR ESTO
  }
  ```

---

## 🧪 Prueba Rápida

Ejecuta este código en la consola del navegador:

```javascript
// 1. Verificar configuración de API
console.log('API_BASE:', API_BASE || 'No definida');

// 2. Probar construcción de URL
const testAnimalId = 58;
const testUrl = `${API_BASE}/animal-images/${testAnimalId}`;
console.log('URL construida:', testUrl);
// Debería mostrar: https://finca.isladigital.xyz/api/v1/animal-images/58

// 3. Verificar token
const token = localStorage.getItem('token') || sessionStorage.getItem('token');
console.log('Token existe:', !!token);
console.log('Token (primeros 20 chars):', token?.substring(0, 20));

// 4. Probar petición GET (para verificar conectividad)
fetch(`${API_BASE}/animal-images/58`, {
  headers: { 'Authorization': `Bearer ${token}` }
})
  .then(r => r.json())
  .then(data => console.log('Respuesta GET:', data))
  .catch(err => console.error('Error GET:', err));
```

---

## 📞 Si el problema persiste

Si después de aplicar estas correcciones sigues teniendo problemas:

1. **Copia el código completo** de tu función de upload
2. **Copia el log de la petición** desde DevTools (Headers + Payload)
3. **Verifica la versión del navegador** (Chrome/Edge ≥ 90 recomendado)

---

## ✅ Cuando funcione correctamente

Verás en los logs del backend:

```
✅ POST /api/v1/animal-images/upload → 200 OK
INFO - Success response: 200 - 1 imagen(es) subida(s) exitosamente
```

Y en la respuesta JSON:

```json
{
  "success": true,
  "message": "1 imagen(es) subida(s) exitosamente",
  "data": {
    "uploaded": [
      {
        "id": 1,
        "filename": "20251018_143022_a3f8e9d1_photo.jpg",
        "url": "https://finca.isladigital.xyz/static/uploads/animals/58/20251018_143022_a3f8e9d1_photo.jpg",
        "size": 245678
      }
    ],
    "total_uploaded": 1,
    "total_errors": 0
  }
}
```

---

## 🎯 Resumen de Cambios Necesarios

**1. En tu archivo de configuración de API:**
```javascript
// Asegúrate de no duplicar /api/v1
const API_BASE = 'https://finca.isladigital.xyz/api/v1';
const ENDPOINTS = {
  uploadImages: '/animal-images/upload', // Sin /api/v1 al inicio
  getImages: (id) => `/animal-images/${id}` // Sin /api/v1 al inicio
};
```

**2. En tu función de upload:**
```javascript
// Añadir animal_id ANTES de los archivos
formData.append('animal_id', animalId);
files.forEach(file => formData.append('files', file));
```

**3. No incluir Content-Type en headers:**
```javascript
headers: {
  'Authorization': `Bearer ${token}`
  // NO añadir Content-Type aquí
}
```
