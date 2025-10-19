import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app
import logging

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
MIME_TYPES = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'webp': 'image/webp',
    'gif': 'image/gif'
}


def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_extension(filename):
    """Obtiene la extensión del archivo"""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return None


def get_mime_type(filename):
    """Obtiene el tipo MIME basado en la extensión del archivo"""
    ext = get_file_extension(filename)
    return MIME_TYPES.get(ext, 'application/octet-stream')


def generate_unique_filename(original_filename):
    """
    Genera un nombre único para el archivo usando timestamp y UUID.
    Formato: timestamp_uuid_original.ext
    """
    ext = get_file_extension(original_filename)
    if not ext:
        ext = 'jpg'  # extensión por defecto

    # Limpiar el nombre original
    safe_name = secure_filename(original_filename)
    base_name = safe_name.rsplit('.', 1)[0] if '.' in safe_name else safe_name

    # Generar nombre único
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]

    return f"{timestamp}_{unique_id}_{base_name}.{ext}"


def get_animal_upload_path(animal_id):
    """
    Genera la ruta de almacenamiento para las imágenes de un animal.
    Formato: static/uploads/animals/{animal_id}/
    """
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
    return os.path.join(upload_folder, 'animals', str(animal_id))


def ensure_upload_directory(directory_path):
    """Crea el directorio de uploads si no existe"""
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creando directorio {directory_path}: {str(e)}")
        return False


def save_animal_image(file, animal_id):
    """
    Guarda una imagen de animal y retorna información del archivo guardado.

    Args:
        file: FileStorage object de werkzeug
        animal_id: ID del animal al que pertenece la imagen

    Returns:
        dict con filename, filepath, file_size, mime_type, o None si hay error
    """
    try:
        # Validar archivo
        if not file or file.filename == '':
            raise ValueError("No se proporcionó ningún archivo")

        if not allowed_file(file.filename):
            raise ValueError(f"Tipo de archivo no permitido. Extensiones permitidas: {', '.join(ALLOWED_EXTENSIONS)}")

        # Validar tamaño
        max_size = current_app.config.get('MAX_IMAGE_SIZE', 5 * 1024 * 1024)  # 5MB por defecto
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            raise ValueError(f"El archivo excede el tamaño máximo permitido de {max_size_mb:.1f}MB")

        # Generar nombre único y ruta
        unique_filename = generate_unique_filename(file.filename)
        upload_dir = get_animal_upload_path(animal_id)

        # Crear directorio si no existe
        if not ensure_upload_directory(upload_dir):
            raise IOError(f"No se pudo crear el directorio de uploads: {upload_dir}")

        # Guardar archivo
        full_path = os.path.join(upload_dir, unique_filename)
        file.save(full_path)

        # Calcular ruta relativa para almacenar en BD
        relative_path = os.path.join('static', 'uploads', 'animals', str(animal_id), unique_filename)
        # Normalizar separadores para URLs (siempre usar /)
        relative_path = relative_path.replace('\\', '/')

        return {
            'filename': unique_filename,
            'filepath': relative_path,
            'file_size': file_size,
            'mime_type': get_mime_type(file.filename)
        }

    except Exception as e:
        logger.error(f"Error guardando imagen para animal {animal_id}: {str(e)}")
        raise


def delete_animal_image(filepath):
    """
    Elimina físicamente un archivo de imagen.

    Args:
        filepath: Ruta relativa del archivo (ej: static/uploads/animals/123/image.jpg)

    Returns:
        bool: True si se eliminó correctamente, False en caso contrario
    """
    try:
        if not filepath:
            return False

        # Construir ruta absoluta
        full_path = os.path.join(current_app.root_path, '..', filepath)
        full_path = os.path.normpath(full_path)

        # Verificar que existe
        if os.path.exists(full_path) and os.path.isfile(full_path):
            os.remove(full_path)
            logger.info(f"Archivo eliminado: {full_path}")
            return True
        else:
            logger.warning(f"Archivo no encontrado: {full_path}")
            return False

    except Exception as e:
        logger.error(f"Error eliminando archivo {filepath}: {str(e)}")
        return False


def get_public_url(filepath):
    """
    Genera la URL pública accesible desde el frontend usando el endpoint público.

    Args:
        filepath: Ruta relativa del archivo

    Returns:
        str: URL completa del archivo
    """
    from flask import request

    # Derivar origen preferentemente desde request.host_url
    try:
        if request and getattr(request, 'host_url', None):
            base_url = (request.host_url or '').rstrip('/')
        elif request and request.host:
            scheme = 'https' if request.is_secure else 'http'
            base_url = f"{scheme}://{request.host}"
        else:
            base_url = current_app.config.get('API_BASE_URL_NO_VERSION', 'http://localhost:5000')
    except Exception:
        base_url = current_app.config.get('API_BASE_URL_NO_VERSION', 'http://localhost:5000')

    # Normalizar filepath y extraer ruta relativa
    relative_path = (filepath or '').replace('\\', '/')
    if relative_path.startswith('static/uploads/'):
        relative_path = relative_path[len('static/uploads/') :]
    return f"{base_url}/public/images/{relative_path}"


def validate_image_count(animal_id, max_images=20):
    """
    Valida que un animal no exceda el número máximo de imágenes permitidas.

    Args:
        animal_id: ID del animal
        max_images: Número máximo de imágenes permitidas

    Returns:
        tuple: (bool, int) - (es_válido, cantidad_actual)
    """
    try:
        from app.models.animal_images import AnimalImages
        current_count = AnimalImages.query.filter_by(animal_id=animal_id).count()
        return (current_count < max_images, current_count)
    except Exception as e:
        logger.error(f"Error validando cantidad de imágenes: {str(e)}")
        return (True, 0)  # En caso de error, permitir la subida
