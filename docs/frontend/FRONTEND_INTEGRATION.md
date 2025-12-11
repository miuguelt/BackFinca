# Guía de Integración Frontend - Sistema de Imágenes

## 🔗 URLs Correctas de la API

**Base URL de la API:** `https://finca.isladigital.xyz/api/v1` (producción) o `http://localhost:8081/api/v1` (desarrollo)

### Endpoints Disponibles:

```javascript
// Configuración base
const API_BASE = 'https://finca.isladigital.xyz/api/v1';
// o para desarrollo local:
// const API_BASE = 'http://localhost:8081/api/v1';

// Endpoints de imágenes de animales
const ENDPOINTS = {
  // Subir imágenes
  uploadImages: `${API_BASE}/animal-images/upload`,

  // Obtener imágenes de un animal
  getAnimalImages: (animalId) => `${API_BASE}/animal-images/${animalId}`,

  // Eliminar una imagen
  deleteImage: (imageId) => `${API_BASE}/animal-images/image/${imageId}`,

  // Establecer imagen como principal
  setPrimaryImage: (imageId) => `${API_BASE}/animal-images/image/${imageId}/set-primary`
};
```

## ⚠️ Error Común Detectado

**Problema:** El frontend está enviando peticiones a `/api/v1/undefined/`

**Causa:** La variable o constante que define el namespace está como `undefined`

**Solución:** Asegúrate de usar las rutas correctas:

```javascript
// ❌ INCORRECTO
const namespace = undefined;
fetch(`${API_BASE}/${namespace}/${animalId}`); // → /api/v1/undefined/58

// ✅ CORRECTO
fetch(`${API_BASE}/animal-images/${animalId}`);
```

## 📦 Archivo de Configuración para React

Crea un archivo `src/config/api.js` o similar:

```javascript
// src/config/api.js
const API_CONFIG = {
  // URL base según el entorno
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8081/api/v1',

  // Endpoints de imágenes de animales
  ANIMAL_IMAGES: {
    UPLOAD: '/animal-images/upload',
    GET_BY_ANIMAL: (animalId) => `/animal-images/${animalId}`,
    DELETE: (imageId) => `/animal-images/image/${imageId}`,
    SET_PRIMARY: (imageId) => `/animal-images/image/${imageId}/set-primary`
  }
};

// Helper para construir URLs completas
export const buildUrl = (endpoint) => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};

export default API_CONFIG;
```

**Uso:**
```javascript
import API_CONFIG, { buildUrl } from '@/config/api';

// Subir imágenes
const uploadUrl = buildUrl(API_CONFIG.ANIMAL_IMAGES.UPLOAD);

// Obtener imágenes de un animal
const getImagesUrl = buildUrl(API_CONFIG.ANIMAL_IMAGES.GET_BY_ANIMAL(animalId));
```

## 🔧 Servicio de API para Imágenes

Crea un servicio dedicado en `src/services/animalImagesService.js`:

```javascript
// src/services/animalImagesService.js
import API_CONFIG, { buildUrl } from '@/config/api';

class AnimalImagesService {
  /**
   * Obtener token de autenticación
   */
  getAuthHeaders() {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    return {
      'Authorization': `Bearer ${token}`
    };
  }

  /**
   * Subir múltiples imágenes para un animal
   * @param {number} animalId - ID del animal
   * @param {File[]} files - Array de archivos
   * @returns {Promise<Object>}
   */
  async uploadImages(animalId, files) {
    const formData = new FormData();
    formData.append('animal_id', animalId);

    // Añadir cada archivo al FormData
    files.forEach(file => {
      formData.append('files', file);
    });

    const response = await fetch(buildUrl(API_CONFIG.ANIMAL_IMAGES.UPLOAD), {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: formData
      // NO incluir 'Content-Type' - el navegador lo establece automáticamente con boundary
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Error al subir imágenes');
    }

    return await response.json();
  }

  /**
   * Obtener todas las imágenes de un animal
   * @param {number} animalId - ID del animal
   * @returns {Promise<Object>}
   */
  async getAnimalImages(animalId) {
    const response = await fetch(
      buildUrl(API_CONFIG.ANIMAL_IMAGES.GET_BY_ANIMAL(animalId)),
      {
        method: 'GET',
        headers: {
          ...this.getAuthHeaders(),
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Error al obtener imágenes');
    }

    return await response.json();
  }

  /**
   * Eliminar una imagen
   * @param {number} imageId - ID de la imagen
   * @returns {Promise<Object>}
   */
  async deleteImage(imageId) {
    const response = await fetch(
      buildUrl(API_CONFIG.ANIMAL_IMAGES.DELETE(imageId)),
      {
        method: 'DELETE',
        headers: {
          ...this.getAuthHeaders(),
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Error al eliminar imagen');
    }

    return await response.json();
  }

  /**
   * Establecer una imagen como principal
   * @param {number} imageId - ID de la imagen
   * @returns {Promise<Object>}
   */
  async setPrimaryImage(imageId) {
    const response = await fetch(
      buildUrl(API_CONFIG.ANIMAL_IMAGES.SET_PRIMARY(imageId)),
      {
        method: 'PUT',
        headers: {
          ...this.getAuthHeaders(),
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Error al establecer imagen principal');
    }

    return await response.json();
  }
}

export default new AnimalImagesService();
```

## 🎨 Componente React: Subir Imágenes

```jsx
// src/components/AnimalImageUpload.jsx
import React, { useState } from 'react';
import animalImagesService from '@/services/animalImagesService';

function AnimalImageUpload({ animalId, onUploadSuccess, onUploadError }) {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [previewUrls, setPreviewUrls] = useState([]);

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(selectedFiles);

    // Crear previews
    const urls = selectedFiles.map(file => URL.createObjectURL(file));
    setPreviewUrls(urls);
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    setUploading(true);

    try {
      const result = await animalImagesService.uploadImages(animalId, files);

      if (result.success) {
        // Limpiar previews
        previewUrls.forEach(url => URL.revokeObjectURL(url));
        setFiles([]);
        setPreviewUrls([]);

        // Notificar éxito
        if (onUploadSuccess) {
          onUploadSuccess(result.data);
        }

        alert(`${result.data.total_uploaded} imagen(es) subida(s) exitosamente`);
      }
    } catch (error) {
      console.error('Error uploading images:', error);
      if (onUploadError) {
        onUploadError(error);
      }
      alert(`Error: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleRemoveFile = (index) => {
    const newFiles = files.filter((_, i) => i !== index);
    const newUrls = previewUrls.filter((_, i) => i !== index);

    // Revocar URL del preview eliminado
    URL.revokeObjectURL(previewUrls[index]);

    setFiles(newFiles);
    setPreviewUrls(newUrls);
  };

  return (
    <div className="animal-image-upload">
      <h3>Subir Imágenes</h3>

      <input
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp,image/gif"
        onChange={handleFileChange}
        disabled={uploading}
        className="file-input"
      />

      {previewUrls.length > 0 && (
        <div className="preview-container">
          <h4>Vista Previa ({files.length} archivo(s))</h4>
          <div className="preview-grid">
            {previewUrls.map((url, index) => (
              <div key={index} className="preview-item">
                <img src={url} alt={`Preview ${index + 1}`} />
                <button
                  onClick={() => handleRemoveFile(index)}
                  className="remove-btn"
                  disabled={uploading}
                >
                  ✕
                </button>
                <span className="file-name">{files[index].name}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={uploading || files.length === 0}
        className="upload-btn"
      >
        {uploading ? 'Subiendo...' : `Subir ${files.length} imagen(es)`}
      </button>
    </div>
  );
}

export default AnimalImageUpload;
```

## 🖼️ Componente React: Galería de Imágenes

```jsx
// src/components/AnimalImageGallery.jsx
import React, { useState, useEffect } from 'react';
import animalImagesService from '@/services/animalImagesService';

function AnimalImageGallery({ animalId }) {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadImages();
  }, [animalId]);

  const loadImages = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await animalImagesService.getAnimalImages(animalId);

      if (result.success) {
        setImages(result.data.images || []);
      }
    } catch (err) {
      console.error('Error loading images:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSetPrimary = async (imageId) => {
    try {
      const result = await animalImagesService.setPrimaryImage(imageId);

      if (result.success) {
        // Recargar imágenes para reflejar el cambio
        await loadImages();
        alert('Imagen establecida como principal');
      }
    } catch (err) {
      console.error('Error setting primary image:', err);
      alert(`Error: ${err.message}`);
    }
  };

  const handleDelete = async (imageId) => {
    if (!confirm('¿Está seguro de eliminar esta imagen?')) return;

    try {
      const result = await animalImagesService.deleteImage(imageId);

      if (result.success) {
        // Recargar imágenes
        await loadImages();
        alert('Imagen eliminada exitosamente');
      }
    } catch (err) {
      console.error('Error deleting image:', err);
      alert(`Error: ${err.message}`);
    }
  };

  if (loading) {
    return <div className="loading">Cargando imágenes...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  if (images.length === 0) {
    return <div className="no-images">No hay imágenes para este animal</div>;
  }

  return (
    <div className="animal-image-gallery">
      <h3>Galería de Imágenes ({images.length})</h3>

      <div className="gallery-grid">
        {images.map(image => (
          <div key={image.id} className="gallery-item">
            <div className="image-wrapper">
              <img
                src={image.url}
                alt={image.filename}
                className="gallery-image"
              />
              {image.is_primary && (
                <span className="primary-badge">Principal</span>
              )}
            </div>

            <div className="image-info">
              <span className="filename">{image.filename}</span>
              <span className="size">
                {(image.file_size / 1024).toFixed(2)} KB
              </span>
            </div>

            <div className="image-actions">
              {!image.is_primary && (
                <button
                  onClick={() => handleSetPrimary(image.id)}
                  className="btn-primary"
                >
                  Establecer como principal
                </button>
              )}
              <button
                onClick={() => handleDelete(image.id)}
                className="btn-danger"
              >
                Eliminar
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default AnimalImageGallery;
```

## 🔍 Debugging

Si sigues teniendo problemas, verifica lo siguiente:

### 1. Verificar en el navegador (DevTools → Network):

```
✅ Correcto:
POST https://finca.isladigital.xyz/api/v1/animal-images/upload
GET  https://finca.isladigital.xyz/api/v1/animal-images/58

❌ Incorrecto:
POST https://finca.isladigital.xyz/api/v1/undefined/upload
GET  https://finca.isladigital.xyz/api/v1/undefined/58
```

### 2. Verificar que el token de autenticación se envía:

```javascript
// En las DevTools → Network → Headers
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### 3. Verificar el formato del FormData para uploads:

```javascript
// En las DevTools → Network → Payload
animal_id: 58
files: (binary)
files: (binary)
```

## 🌐 Variables de Entorno

En tu archivo `.env` o `.env.local` de React:

```bash
# Desarrollo local
VITE_API_BASE_URL=http://localhost:8081/api/v1

# Producción
# VITE_API_BASE_URL=https://finca.isladigital.xyz/api/v1
```

## ✅ Checklist de Integración

- [ ] Archivo de configuración `api.js` creado con las rutas correctas
- [ ] Servicio `animalImagesService.js` implementado
- [ ] Componente de subida de imágenes funcional
- [ ] Componente de galería implementado
- [ ] Variable de entorno `VITE_API_BASE_URL` configurada
- [ ] Token de autenticación se envía en todas las peticiones
- [ ] URLs verificadas en DevTools (sin `undefined`)
- [ ] Manejo de errores implementado
- [ ] Feedback visual al usuario (loading, success, error)

## 📞 Soporte

Si tienes problemas:

1. Verifica los logs del backend en la consola
2. Verifica las peticiones en las DevTools del navegador
3. Asegúrate de que el animal existe antes de subir imágenes
4. Verifica que el token de autenticación sea válido

**Documentación completa:** Ver `ANIMAL_IMAGES_USAGE.md`
