# Solución para mostrar imágenes en el frontend

## Problema identificado

Las imágenes del animal 52 no se mostraban en el frontend debido a varios problemas:

1. **Protección de archivos estáticos**: El middleware de seguridad estaba protegiendo las rutas `/static/` con autenticación JWT
2. **Configuración de JWT en producción**: Solo aceptaba cookies, no headers de Authorization
3. **Generación de URLs**: Las URLs generadas apuntaban a rutas protegidas
4. **Middleware de inyección de tokens**: Estaba causando conflictos en las respuestas JSON

## Cambios realizados

### 1. Agregado endpoint público para imágenes

**Archivo**: `app/__init__.py`
- Se agregó el endpoint `/public/images/<path>` que sirve imágenes sin requerir autenticación
- Este endpoint accede directamente a los archivos en `static/uploads/`

### 2. Modificado modelo AnimalImages

**Archivo**: `app/models/animal_images.py`
- Actualizado el método `to_namespace_dict()` para generar URLs usando el nuevo endpoint público
- Las URLs ahora tienen el formato: `https://finca.enlinea.sbs/public/images/animals/52/filename.png`

### 3. Actualizada función de utilidad

**Archivo**: `app/utils/file_storage.py`
- Modificada la función `get_public_url()` para usar el nuevo endpoint público
- Extrae la ruta relativa y genera URLs públicas

### 4. Configuración de seguridad

**Archivo**: `app/utils/security_middleware.py`
- Agregadas rutas `/static` y `/public` a la lista blanca de rutas públicas
- Agregado wildcard para permitir todas las subrutas de `/public/`

### 5. Configuración de JWT

**Archivo**: `config.py`
- Modificada la configuración de producción para aceptar tanto cookies como headers de Authorization
- Cambiado: `JWT_TOKEN_LOCATION = ['cookies']` → `JWT_TOKEN_LOCATION = ['cookies', 'headers']`

### 6. Middleware de inyección de tokens

**Archivo**: `app/__init__.py`
- Modificado el middleware `attach_access_token_to_json` para no inyectar tokens en respuestas APIResponse
- Esto evita conflictos en las respuestas JSON estructuradas

### 7. Configuración de URLs

**Archivo**: `.env`
- Agregada la variable `API_BASE_URL_NO_VERSION=https://finca.enlinea.sbs`

## URLs de las imágenes del animal 52

Las imágenes del animal 52 ahora son accesibles públicamente en:

1. `https://finca.enlinea.sbs/public/images/animals/52/20251018_083235_90993378_2025-07-22_16.53.54_senasofiaplus.edu.co_858e50588c64.png`
2. `https://finca.enlinea.sbs/public/images/animals/52/20251018_083315_32f1765b_unnamed.png`
3. `https://finca.enlinea.sbs/public/images/animals/52/20251018_090725_762e8b36_unnamed.png`

## Para el frontend

### 1. Obtener las imágenes del animal

Usar el endpoint autenticado:
```
GET /api/v1/animal-images/52
Headers: Authorization: Bearer {token}
```

### 2. Respuesta esperada

```json
{
  "success": true,
  "message": "3 imagen(es) encontrada(s)",
  "data": {
    "animal_id": 52,
    "total": 3,
    "images": [
      {
        "id": 1,
        "animal_id": 52,
        "filename": "20251018_083235_90993378_2025-07-22_16.53.54_senasofiaplus.edu.co_858e50588c64.png",
        "filepath": "static/uploads/animals/52/20251018_083235_90993378_2025-07-22_16.53.54_senasofiaplus.edu.co_858e50588c64.png",
        "file_size": 1835659,
        "mime_type": "image/png",
        "is_primary": true,
        "url": "https://finca.enlinea.sbs/public/images/animals/52/20251018_083235_90993378_2025-07-22_16.53.54_senasofiaplus.edu.co_858e50588c64.png",
        "created_at": "2025-10-18T08:32:35.000Z"
      },
      // ... otras imágenes
    ]
  }
}
```

### 3. Mostrar las imágenes

Usar el campo `url` de cada imagen en el atributo `src` de las etiquetas `<img>`:

```javascript
// Ejemplo en React
{images.map(img => (
  <img key={img.id} src={img.url} alt={`Imagen ${img.id}`} />
))}
```

## Pasos necesarios

1. **Reiniciar el servidor** para aplicar todos los cambios de configuración
2. **Probar el endpoint** `/api/v1/animal-images/52` con autenticación
3. **Verificar que las URLs** generadas sean accesibles públicamente
4. **Actualizar el frontend** para usar las URLs del campo `url` en las respuestas

## Verificación

Para verificar que todo funciona correctamente:

1. Las imágenes deben ser accesibles directamente sin autenticación
2. El endpoint `/api/v1/animal-images/52` debe devolver las URLs correctas
3. El frontend debe poder mostrar las imágenes usando las URLs proporcionadas

## Notas importantes

- Las URLs públicas son seguras porque solo acceden a archivos de imágenes
- No se requiere autenticación para acceder a las imágenes (performance mejor)
- El endpoint de API para obtener los metadatos de las imágenes sigue requiriendo autenticación
- Los cambios son compatibles con el funcionamiento existente de la aplicación