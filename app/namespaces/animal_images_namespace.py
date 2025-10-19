from flask import request, current_app
from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required
import logging

from app import db
from app.models.animals import Animals
from app.models.animal_images import AnimalImages
from app.utils.response_handler import APIResponse
from app.utils.file_storage import (
    save_animal_image,
    delete_animal_image,
    get_public_url,
    validate_image_count,
    allowed_file
)

logger = logging.getLogger(__name__)

# Crear namespace
animal_images_ns = Namespace(
    'animal-images',
    description='Operaciones con imágenes de animales',
    path='/animal-images'
)

# Modelos para documentación
image_model = animal_images_ns.model('AnimalImage', {
    'id': fields.Integer(description='ID de la imagen'),
    'animal_id': fields.Integer(required=True, description='ID del animal'),
    'filename': fields.String(description='Nombre del archivo'),
    'filepath': fields.String(description='Ruta del archivo'),
    'file_size': fields.Integer(description='Tamaño del archivo en bytes'),
    'mime_type': fields.String(description='Tipo MIME del archivo'),
    'is_primary': fields.Boolean(description='Si es la imagen principal'),
    'url': fields.String(description='URL pública de la imagen'),
    'created_at': fields.DateTime(description='Fecha de creación')
})


@animal_images_ns.route('/upload')
class ImageUpload(Resource):
    @jwt_required()
    @animal_images_ns.doc(
        description='Subir múltiples imágenes para un animal',
        params={
            'animal_id': 'ID del animal (form field)',
            'files': 'Archivos de imagen (multipart/form-data)'
        }
    )
    def post(self):
        """Subir múltiples imágenes para un animal"""
        try:
            # Obtener animal_id del formulario
            animal_id = request.form.get('animal_id', type=int)
            if not animal_id:
                return APIResponse.error(
                    message='El campo animal_id es requerido',
                    status_code=400
                )

            # Validar que el animal existe
            animal = Animals.query.get(animal_id)
            if not animal:
                return APIResponse.error(
                    message=f'Animal con ID {animal_id} no encontrado',
                    status_code=404
                )

            # Validar cantidad de imágenes actuales
            max_images = current_app.config.get('MAX_IMAGES_PER_ANIMAL', 20)
            is_valid, current_count = validate_image_count(animal_id, max_images)

            # Obtener archivos
            files = request.files.getlist('files')
            if not files or len(files) == 0:
                return APIResponse.error(
                    message='No se proporcionaron archivos',
                    status_code=400
                )

            # Validar que no exceda el máximo
            if current_count + len(files) > max_images:
                return APIResponse.error(
                    message=f'Excede el límite de {max_images} imágenes por animal. Actualmente tiene {current_count} imágenes.',
                    status_code=400
                )

            uploaded_images = []
            errors = []

            # Procesar cada archivo
            for file in files:
                try:
                    # Validar archivo
                    if not file or file.filename == '':
                        errors.append({'filename': 'unknown', 'error': 'Archivo vacío'})
                        continue

                    if not allowed_file(file.filename):
                        errors.append({
                            'filename': file.filename,
                            'error': 'Tipo de archivo no permitido'
                        })
                        continue

                    # Guardar archivo
                    file_info = save_animal_image(file, animal_id)

                    # Crear registro en BD
                    image = AnimalImages(
                        animal_id=animal_id,
                        filename=file_info['filename'],
                        filepath=file_info['filepath'],
                        file_size=file_info['file_size'],
                        mime_type=file_info['mime_type'],
                        is_primary=False  # Por defecto no es principal
                    )

                    db.session.add(image)
                    db.session.flush()

                    uploaded_images.append({
                        'id': image.id,
                        'filename': image.filename,
                        'url': get_public_url(image.filepath),
                        'size': image.file_size
                    })

                except Exception as e:
                    logger.error(f"Error procesando archivo {file.filename}: {str(e)}")
                    errors.append({
                        'filename': file.filename,
                        'error': str(e)
                    })

            # Commit si hubo al menos una imagen exitosa
            if uploaded_images:
                db.session.commit()

                # Si es la primera imagen del animal, marcarla como principal
                if current_count == 0 and len(uploaded_images) > 0:
                    first_image = AnimalImages.query.get(uploaded_images[0]['id'])
                    if first_image:
                        first_image.is_primary = True
                        db.session.commit()

            else:
                db.session.rollback()

            # Preparar respuesta
            response_data = {
                'uploaded': uploaded_images,
                'total_uploaded': len(uploaded_images),
                'total_errors': len(errors),
                'errors': errors if errors else None
            }

            if len(uploaded_images) > 0:
                message = f'{len(uploaded_images)} imagen(es) subida(s) exitosamente'
                if errors:
                    message += f' ({len(errors)} error(es))'
                return APIResponse.success(data=response_data, message=message)
            else:
                return APIResponse.error(
                    message='No se pudo subir ninguna imagen',
                    data=response_data,
                    status_code=400
                )

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error en upload de imágenes: {str(e)}")
            return APIResponse.error(
                message=f'Error al subir imágenes: {str(e)}',
                status_code=500
            )


@animal_images_ns.route('/<int:animal_id>')
class AnimalImagesList(Resource):
    @jwt_required()
    @animal_images_ns.doc(description='Obtener todas las imágenes de un animal')
    def get(self, animal_id):
        """Obtener todas las imágenes de un animal"""
        try:
            # Validar que el animal existe
            animal = Animals.query.get(animal_id)
            if not animal:
                return APIResponse.error(
                    message=f'Animal con ID {animal_id} no encontrado',
                    status_code=404
                )

            # Obtener imágenes ordenadas (primero la principal, luego por fecha)
            images = AnimalImages.query.filter_by(animal_id=animal_id)\
                .order_by(AnimalImages.is_primary.desc(), AnimalImages.created_at.desc())\
                .all()

            # Serializar con URLs públicas
            images_data = [image.to_namespace_dict() for image in images]

            # Incluir origen del servidor para frontend (construcción de recursos)
            server_origin = (request.host_url or '').rstrip('/') if request else current_app.config.get('API_BASE_URL_NO_VERSION', '').rstrip('/')
            return APIResponse.success(
                data={
                    'animal_id': animal_id,
                    'total': len(images_data),
                    'images': images_data,
                    'base_url': server_origin
                },
                message=f'{len(images_data)} imagen(es) encontrada(s)'
            )

        except Exception as e:
            logger.error(f"Error obteniendo imágenes del animal {animal_id}: {str(e)}")
            return APIResponse.error(
                message=f'Error al obtener imágenes: {str(e)}',
                status_code=500
            )


@animal_images_ns.route('/image/<int:image_id>')
class AnimalImageDetail(Resource):
    @jwt_required()
    @animal_images_ns.doc(description='Eliminar una imagen específica')
    def delete(self, image_id):
        """Eliminar una imagen"""
        try:
            # Buscar la imagen
            image = AnimalImages.query.get(image_id)
            if not image:
                return APIResponse.error(
                    message=f'Imagen con ID {image_id} no encontrada',
                    status_code=404
                )

            animal_id = image.animal_id
            was_primary = image.is_primary
            filepath = image.filepath

            # Eliminar registro de BD
            db.session.delete(image)
            db.session.commit()

            # Eliminar archivo físico
            delete_animal_image(filepath)

            # Si era la imagen principal, asignar otra como principal
            if was_primary:
                next_image = AnimalImages.query.filter_by(animal_id=animal_id)\
                    .order_by(AnimalImages.created_at.desc())\
                    .first()
                if next_image:
                    next_image.is_primary = True
                    db.session.commit()

            return APIResponse.success(
                message='Imagen eliminada exitosamente',
                data={'id': image_id, 'animal_id': animal_id}
            )

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error eliminando imagen {image_id}: {str(e)}")
            return APIResponse.error(
                message=f'Error al eliminar imagen: {str(e)}',
                status_code=500
            )


@animal_images_ns.route('/image/<int:image_id>/set-primary')
class SetPrimaryImage(Resource):
    @jwt_required()
    @animal_images_ns.doc(description='Establecer una imagen como principal')
    def put(self, image_id):
        """Establecer una imagen como principal del animal"""
        try:
            # Buscar la imagen
            image = AnimalImages.query.get(image_id)
            if not image:
                return APIResponse.error(
                    message=f'Imagen con ID {image_id} no encontrada',
                    status_code=404
                )

            # Quitar marca de principal a todas las imágenes del animal
            AnimalImages.query.filter_by(animal_id=image.animal_id)\
                .update({'is_primary': False})

            # Marcar esta imagen como principal
            image.is_primary = True
            db.session.commit()

            return APIResponse.success(
                message='Imagen establecida como principal',
                data=image.to_namespace_dict()
            )

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error estableciendo imagen principal {image_id}: {str(e)}")
            return APIResponse.error(
                message=f'Error al establecer imagen principal: {str(e)}',
                status_code=500
            )
