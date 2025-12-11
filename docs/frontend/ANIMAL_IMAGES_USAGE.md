# Sistema de Imágenes para Animales

## Descripción

Sistema completo para gestionar imágenes de animales con soporte para múltiples imágenes por animal, almacenamiento organizado y URLs accesibles desde el frontend.

## Características

- ✅ Subida de múltiples imágenes por animal
- ✅ Almacenamiento organizado por `animal_id`: `static/uploads/animals/{animal_id}/`
- ✅ Nombres únicos para evitar colisiones (timestamp + UUID)
- ✅ Validación de tipo y tamaño de archivo
- ✅ Imagen principal (primary) por animal
- ✅ URLs públicas accesibles desde React
- ✅ Cascade delete automático
- ✅ Optimización con índices en BD

## Endpoints

### 1. Subir imágenes

**POST** `/api/v1/animal-images/upload`

**Headers:**
```
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Form Data:**
- `animal_id` (integer, required): ID del animal
- `files` (files[], required): Uno o más archivos de imagen

**Ejemplo con cURL:**
```bash
curl -X POST http://localhost:8081/api/v1/animal-images/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "animal_id=123" \
  -F "files=@/path/to/image1.jpg" \
  -F "files=@/path/to/image2.png"
```

**Ejemplo con JavaScript (FormData):**
```javascript
const formData = new FormData();
formData.append('animal_id', animalId);

// Añadir múltiples archivos
for (const file of files) {
  formData.append('files', file);
}

const response = await fetch('/api/v1/animal-images/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});

const result = await response.json();
console.log(result.data);
```

**Respuesta exitosa:**
```json
{
  "success": true,
  "message": "2 imagen(es) subida(s) exitosamente",
  "data": {
    "uploaded": [
      {
        "id": 1,
        "filename": "20251018_143022_a3f8e9d1_photo.jpg",
        "url": "https://api.example.com/static/uploads/animals/123/20251018_143022_a3f8e9d1_photo.jpg",
        "size": 245678
      },
      {
        "id": 2,
        "filename": "20251018_143023_b7c2d4a6_portrait.png",
        "url": "https://api.example.com/static/uploads/animals/123/20251018_143023_b7c2d4a6_portrait.png",
        "size": 189234
      }
    ],
    "total_uploaded": 2,
    "total_errors": 0,
    "errors": null
  }
}
```

### 2. Obtener imágenes de un animal

**GET** `/api/v1/animal-images/{animal_id}`

**Headers:**
```
Authorization: Bearer <token>
```

**Ejemplo:**
```bash
curl -X GET http://localhost:8081/api/v1/animal-images/123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Respuesta:**
```json
{
  "success": true,
  "message": "2 imagen(es) encontrada(s)",
  "data": {
    "animal_id": 123,
    "total": 2,
    "images": [
      {
        "id": 1,
        "animal_id": 123,
        "filename": "20251018_143022_a3f8e9d1_photo.jpg",
        "filepath": "static/uploads/animals/123/20251018_143022_a3f8e9d1_photo.jpg",
        "file_size": 245678,
        "mime_type": "image/jpeg",
        "is_primary": true,
        "url": "https://api.example.com/static/uploads/animals/123/20251018_143022_a3f8e9d1_photo.jpg",
        "created_at": "2025-10-18T14:30:22Z",
        "updated_at": "2025-10-18T14:30:22Z"
      },
      {
        "id": 2,
        "animal_id": 123,
        "filename": "20251018_143023_b7c2d4a6_portrait.png",
        "filepath": "static/uploads/animals/123/20251018_143023_b7c2d4a6_portrait.png",
        "file_size": 189234,
        "mime_type": "image/png",
        "is_primary": false,
        "url": "https://api.example.com/static/uploads/animals/123/20251018_143023_b7c2d4a6_portrait.png",
        "created_at": "2025-10-18T14:30:23Z",
        "updated_at": "2025-10-18T14:30:23Z"
      }
    ]
  }
}
```

### 3. Eliminar una imagen

**DELETE** `/api/v1/animal-images/image/{image_id}`

**Headers:**
```
Authorization: Bearer <token>
```

**Ejemplo:**
```bash
curl -X DELETE http://localhost:8081/api/v1/animal-images/image/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Imagen eliminada exitosamente",
  "data": {
    "id": 1,
    "animal_id": 123
  }
}
```

### 4. Establecer imagen principal

**PUT** `/api/v1/animal-images/image/{image_id}/set-primary`

**Headers:**
```
Authorization: Bearer <token>
```

**Ejemplo:**
```bash
curl -X PUT http://localhost:8081/api/v1/animal-images/image/2/set-primary \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Imagen establecida como principal",
  "data": {
    "id": 2,
    "animal_id": 123,
    "is_primary": true,
    ...
  }
}
```

## Validaciones

### Tipos de archivo permitidos
- `.jpg` / `.jpeg`
- `.png`
- `.webp`
- `.gif`

### Límites
- **Tamaño máximo por archivo:** 5 MB
- **Máximo de imágenes por animal:** 20

### Errores comunes

**400 - Bad Request:**
```json
{
  "success": false,
  "error": "validation_error",
  "message": "El campo animal_id es requerido"
}
```

**404 - Not Found:**
```json
{
  "success": false,
  "error": "not_found",
  "message": "Animal con ID 999 no encontrado"
}
```

**413 - Payload Too Large:**
```json
{
  "success": false,
  "error": "file_too_large",
  "message": "El archivo excede el tamaño máximo permitido de 5.0MB"
}
```

## Integración con React

### Componente de subida de imágenes

```jsx
import React, { useState } from 'react';

function AnimalImageUpload({ animalId, onUploadSuccess }) {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
  };

  const handleUpload = async () => {
    setUploading(true);

    const formData = new FormData();
    formData.append('animal_id', animalId);

    files.forEach(file => {
      formData.append('files', file);
    });

    try {
      const response = await fetch('/api/v1/animal-images/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
      });

      const result = await response.json();

      if (result.success) {
        onUploadSuccess(result.data.uploaded);
        setFiles([]);
      } else {
        alert(`Error: ${result.message}`);
      }
    } catch (error) {
      console.error('Error uploading images:', error);
      alert('Error al subir imágenes');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <input
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp,image/gif"
        onChange={handleFileChange}
        disabled={uploading}
      />
      <button onClick={handleUpload} disabled={uploading || files.length === 0}>
        {uploading ? 'Subiendo...' : `Subir ${files.length} imagen(es)`}
      </button>
    </div>
  );
}

export default AnimalImageUpload;
```

### Componente de galería

```jsx
import React, { useState, useEffect } from 'react';

function AnimalImageGallery({ animalId }) {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchImages();
  }, [animalId]);

  const fetchImages = async () => {
    try {
      const response = await fetch(`/api/v1/animal-images/${animalId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      const result = await response.json();

      if (result.success) {
        setImages(result.data.images);
      }
    } catch (error) {
      console.error('Error fetching images:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSetPrimary = async (imageId) => {
    try {
      const response = await fetch(`/api/v1/animal-images/image/${imageId}/set-primary`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        fetchImages(); // Recargar imágenes
      }
    } catch (error) {
      console.error('Error setting primary image:', error);
    }
  };

  const handleDelete = async (imageId) => {
    if (!confirm('¿Está seguro de eliminar esta imagen?')) return;

    try {
      const response = await fetch(`/api/v1/animal-images/image/${imageId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        fetchImages(); // Recargar imágenes
      }
    } catch (error) {
      console.error('Error deleting image:', error);
    }
  };

  if (loading) return <div>Cargando imágenes...</div>;

  return (
    <div className="image-gallery">
      {images.map(image => (
        <div key={image.id} className="image-card">
          <img src={image.url} alt={image.filename} />
          {image.is_primary && <span className="badge">Principal</span>}
          <div className="actions">
            {!image.is_primary && (
              <button onClick={() => handleSetPrimary(image.id)}>
                Establecer como principal
              </button>
            )}
            <button onClick={() => handleDelete(image.id)}>
              Eliminar
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

export default AnimalImageGallery;
```

## Estructura de Base de Datos

```sql
CREATE TABLE animal_images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    animal_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(500) NOT NULL,
    file_size INT,
    mime_type VARCHAR(100),
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (animal_id) REFERENCES animals(id) ON DELETE CASCADE,

    INDEX ix_animal_images_animal_id (animal_id),
    INDEX ix_animal_images_is_primary (is_primary),
    INDEX ix_animal_images_created_at (created_at)
);
```

## Configuración

Las siguientes configuraciones están disponibles en `config.py`:

```python
# Carpeta de uploads
UPLOAD_FOLDER = 'static/uploads'

# Tamaño máximo de imagen (5MB)
MAX_IMAGE_SIZE = 5 * 1024 * 1024

# Extensiones permitidas
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}

# Máximo de imágenes por animal
MAX_IMAGES_PER_ANIMAL = 20
```

## Notas Importantes

1. **Cascade Delete:** Al eliminar un animal, todas sus imágenes se eliminan automáticamente (tanto de la BD como del sistema de archivos).

2. **Imagen Principal:** La primera imagen subida se marca automáticamente como principal. Solo puede haber una imagen principal por animal.

3. **Nombres de Archivo:** Los archivos se renombran automáticamente con el formato: `YYYYMMDD_HHMMSS_{uuid}_{nombre_original}.ext`

4. **URLs Públicas:** Las URLs generadas son accesibles directamente desde el navegador a través de la ruta `/static/uploads/animals/{animal_id}/{filename}`.

5. **Seguridad:** Todos los endpoints requieren autenticación JWT.
