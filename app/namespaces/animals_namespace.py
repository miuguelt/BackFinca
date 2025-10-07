from flask import request
from flask_restx import Resource, Namespace, fields
import sqlalchemy as sa
from sqlalchemy import and_
from app import db
from flask_jwt_extended import jwt_required, get_jwt_identity

# Asumir que animal_model está definido en modelos o utils
from app.models.animals import Animals
from app.utils.response_handler import APIResponse
from app.utils.namespace_helpers import create_optimized_namespace, _cache_clear
from app.utils.tree_builder import build_ancestor_tree, build_descendant_tree, invalidate_animal_tree_cache_for
from app.utils.integrity_checker import OptimizedIntegrityChecker

# Helper para mapear campos del frontend al backend
def map_frontend_filters(filters):
    """Mapea nombres de campos del frontend a nombres del backend."""
    if not filters:
        return filters
    
    mapped_filters = filters.copy()
    field_mapping = {
        'father_id': 'idFather',
        'mother_id': 'idMother',
        # Nota: animal_id es el campo correcto en las tablas hijas, no animals_id
        # Este mapeo se eliminó para evitar conflictos con el cacheo
    }
    
    for frontend_field, backend_field in field_mapping.items():
        if frontend_field in mapped_filters:
            mapped_filters[backend_field] = mapped_filters.pop(frontend_field)
    
    return mapped_filters

animals_ns = create_optimized_namespace(
    name='animals',
    description='Animals operations',
    model_class=Animals,
    path='/animals'
)

animal_model = animals_ns.model('Animal', {
    'record': fields.String(required=True),
    'sex': fields.String(required=True),
    'birth_date': fields.Date(required=True),
    'weight': fields.Float(required=True),
    'status': fields.String(default='active'),
    'breeds_id': fields.Integer(required=True),
    # Agregar otros campos según el modelo
})

# Deshabilitado: CRUD estándar manejado por create_optimized_namespace
# @animals_ns.route('/')
class AnimalsList(Resource):
    @jwt_required()
    def get(self):
        try:
            page = request.args.get('page', default=1, type=int) or 1
            limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50
            search = request.args.get('search', '')

            # Mapear posibles filtros del frontend a los campos del backend
            filters = map_frontend_filters(dict(request.args))

            # Usar el constructor de consulta del BaseModel para un orden determinista
            query_or_paginated = Animals.get_namespace_query(
                filters=filters,
                search=(search or None),
                search_type='all',
                sort_by='updated_at',
                sort_order='desc',
                page=page,
                per_page=int(limit),
                include_relations=False,
            )

            data_struct = Animals.get_paginated_response(query_or_paginated, include_relations=False)

            # Respuesta estandarizada con metadatos de paginación
            return APIResponse.paginated_success(
                data=data_struct.get('items', []),
                page=data_struct.get('page', 1),
                limit=data_struct.get('limit', data_struct.get('per_page', len(data_struct.get('items', [])))),
                total_items=data_struct.get('total_items', data_struct.get('total', 0)),
                message='Lista de animales obtenida exitosamente'
            )
        except Exception as e:
            return APIResponse.error(message=f'Error al obtener animales: {str(e)}')
    
    @jwt_required()
    @animals_ns.expect(animal_model)
    def post(self):
        try:
            data = request.get_json()
            
            # Validar datos requeridos
            required_fields = ['sex', 'birth_date', 'weight', 'record', 'breeds_id']
            for field in required_fields:
                if field not in data or not data[field]:
                    return APIResponse.error(message=f'El campo {field} es requerido')
            
            # Crear nuevo animal
            animal = Animals(**data)
            db.session.add(animal)
            db.session.flush()  # Obtener ID generado
            db.session.commit()  # Persistir en BD
            db.session.refresh(animal)  # Sincronizar con BD
            # Invalida todas las variantes de caché relacionadas con Animals
            _cache_clear(Animals)
            # Invalidar caché de árboles relacionados
            try:
                invalidate_animal_tree_cache_for(animal.id)
                if animal.idFather:
                    invalidate_animal_tree_cache_for(animal.idFather)
                if animal.idMother:
                    invalidate_animal_tree_cache_for(animal.idMother)
            except Exception:
                pass

            return APIResponse.success(
                data=animal.to_namespace_dict(),
                message='Animal creado correctamente'
            )
        except Exception as e:
            db.session.rollback()
            return APIResponse.error(message=f'Error al crear animal: {str(e)}')

# @animals_ns.route('/<int:record_id>')
class AnimalDetail(Resource):
    @jwt_required()
    def get(self, record_id):
        try:
            animal = Animals.query.get_or_404(record_id)
            return APIResponse.success(data=animal.to_namespace_dict())
        except Exception as e:
            return APIResponse.error(message=f'Error al obtener animal: {str(e)}')

    @jwt_required()
    @animals_ns.expect(animal_model)
    def put(self, record_id):
        try:
            animal = Animals.query.get_or_404(record_id)
            data = request.get_json()
            for key, value in data.items():
                setattr(animal, key, value)
            db.session.flush()  # Aplicar cambios
            db.session.commit()  # Persistir en BD
            db.session.refresh(animal)  # Sincronizar con BD
            # Invalida todas las variantes de caché relacionadas con Animals
            _cache_clear(Animals)
            # Invalidar caché de árboles relacionados
            try:
                invalidate_animal_tree_cache_for(animal.id)
                if animal.idFather:
                    invalidate_animal_tree_cache_for(animal.idFather)
                if animal.idMother:
                    invalidate_animal_tree_cache_for(animal.idMother)
            except Exception:
                pass
            return APIResponse.success(data=animal.to_namespace_dict(), message='Animal actualizado correctamente')
        except Exception as e:
            db.session.rollback()
            return APIResponse.error(message=f'Error al actualizar animal: {str(e)}')

    @jwt_required()
    def delete(self, record_id):
        try:
            animal = Animals.query.get_or_404(record_id)
            db.session.delete(animal)
            db.session.commit()
            # Invalida todas las variantes de caché relacionadas con Animals
            _cache_clear(Animals)
            # Invalidar caché de árboles relacionados
            try:
                invalidate_animal_tree_cache_for(record_id)
                if getattr(animal, 'idFather', None):
                    invalidate_animal_tree_cache_for(animal.idFather)
                if getattr(animal, 'idMother', None):
                    invalidate_animal_tree_cache_for(animal.idMother)
            except Exception:
                pass
            return APIResponse.success(message='Animal eliminado correctamente')
        except Exception as e:
            db.session.rollback()
            return APIResponse.error(message=f'Error al eliminar animal: {str(e)}')

@animals_ns.route('/<int:animal_id>/dependencies')
class AnimalDependencies(Resource):
    @jwt_required()
    def get(self, animal_id):
        """
        Verificación ultra-rápida de dependencias usando EXISTS optimizado.
        Compatible con frontend que usa father_id/mother_id.
        """
        try:
            # Verificar si el animal existe
            animal = Animals.query.get(animal_id)
            if not animal:
                return APIResponse.error(message=f'Animal con ID {animal_id} no encontrado', status_code=404)
            
            # Usar el integrity checker ultra-optimizado con EXISTS
            warnings = OptimizedIntegrityChecker.check_integrity_fast(Animals, animal_id)
            
            # Convertir warnings al formato esperado por el frontend
            dependencies = []
            total_count = 0
            
            for warning in warnings:
                # Mapear nombres de campos para compatibilidad con frontend
                field_name = warning.dependent_field
                if field_name == 'idFather':
                    field_name = 'father_id'
                elif field_name == 'idMother':
                    field_name = 'mother_id'
                elif field_name == 'animals_id':
                    field_name = 'animal_id'
                
                dependencies.append({
                    'table': warning.dependent_table,
                    'count': warning.dependent_count,
                    'field': field_name,
                    'cascade_delete': warning.cascade_delete,
                    'message': warning.warning_message
                })
                total_count += warning.dependent_count
            
            # Determinar si se puede eliminar
            can_delete = all(warning.cascade_delete for warning in warnings)
            
            # Construir mensaje apropiado
            if can_delete and total_count > 0:
                message = f"Se eliminarán automáticamente {total_count} registro(s) relacionado(s)."
            elif can_delete:
                message = "Este animal puede ser eliminado safely."
            else:
                message = f"No se puede eliminar este animal porque tiene {total_count} registro(s) relacionado(s)."
            
            return APIResponse.success(
                data={
                    'id': animal_id,
                    'hasDependencies': total_count > 0,
                    'canDelete': can_delete,
                    'totalDependencies': total_count,
                    'message': message,
                    'dependencies': dependencies
                },
                message='Dependencias verificadas exitosamente'
            )
            
        except Exception as e:
            return APIResponse.error(
                message=f'Error al verificar dependencias del animal: {str(e)}',
                status_code=500
            )

@animals_ns.route('/<int:animal_id>/delete-with-check')
class AnimalDeleteWithCheck(Resource):
    @jwt_required()
    def delete(self, animal_id):
        """
        Eliminación ultra-optimizada que verifica dependencias y elimina en una sola operación.
        Usa EXISTS para verificación y transacción atómica para eliminación.
        """
        try:
            # Verificar si el animal existe
            animal = Animals.query.get(animal_id)
            if not animal:
                return APIResponse.error(message=f'Animal con ID {animal_id} no encontrado', status_code=404)
            
            # Verificación ultra-rápida de dependencias
            warnings = OptimizedIntegrityChecker.check_integrity_fast(Animals, animal_id)
            
            # Verificar si se puede eliminar
            can_delete = all(warning.cascade_delete for warning in warnings)
            total_dependencies = sum(warning.dependent_count for warning in warnings)
            
            if not can_delete:
                # Construir mensaje de error detallado
                blocking_deps = [w for w in warnings if not w.cascade_delete]
                message = f"No se puede eliminar: {len(blocking_deps)} tipo(s) de dependencias bloquean la eliminación."
                
                return APIResponse.error(
                    message=message,
                    data={
                        'id': animal_id,
                        'canDelete': False,
                        'totalDependencies': total_dependencies,
                        'blockingDependencies': len(blocking_deps),
                        'dependencies': [
                            {
                                'table': w.dependent_table,
                                'count': w.dependent_count,
                                'field': w.dependent_field,
                                'message': w.warning_message
                            } for w in blocking_deps
                        ]
                    },
                    status_code=409  # Conflict
                )
            
            # Eliminación en transacción atómica
            try:
                # Iniciar transacción
                db.session.begin_nested()
                
                # Eliminar el animal (las dependencias en cascade se eliminarán automáticamente)
                db.session.delete(animal)
                
                # Confirmar transacción
                db.session.commit()
                # Invalida todas las variantes de caché relacionadas con Animals
                _cache_clear(Animals)
                
                # Limpiar cache para este animal
                cache_key = OptimizedIntegrityChecker._get_cache_key(Animals, animal_id)
                if cache_key in OptimizedIntegrityChecker._cache:
                    del OptimizedIntegrityChecker._cache[cache_key]
                if cache_key in OptimizedIntegrityChecker._cache_timestamps:
                    del OptimizedIntegrityChecker._cache_timestamps[cache_key]
                
                return APIResponse.success(
                    data={
                        'id': animal_id,
                        'deleted': True,
                        'cascadeDeleted': total_dependencies,
                        'message': f'Animal eliminado exitosamente con {total_dependencies} dependencia(s) en cascade.'
                    },
                    message='Animal eliminado exitosamente'
                )
                
            except Exception as e:
                # Rollback en caso de error
                db.session.rollback()
                raise e
                
        except Exception as e:
            db.session.rollback()
            return APIResponse.error(
                message=f'Error al eliminar animal: {str(e)}',
                status_code=500
            )

@animals_ns.route('/batch-dependencies')
class AnimalBatchDependencies(Resource):
    @jwt_required()
    def post(self):
        """
        Verificación batch de dependencias para múltiples animales.
        Ultra-optimizado con UNION ALL y cache compartido.
        """
        try:
            data = request.get_json()
            animal_ids = data.get('animal_ids', [])
            
            if not animal_ids:
                return APIResponse.error(message='Se requiere lista de animal_ids', status_code=400)
            
            if len(animal_ids) > 100:
                return APIResponse.error(message='Máximo 100 animales por consulta', status_code=400)
            
            results = {}
            
            # Verificar que los animales existan
            animals = Animals.query.filter(Animals.id.in_(animal_ids)).all()
            existing_ids = {animal.id for animal in animals}
            
            for animal_id in animal_ids:
                if animal_id not in existing_ids:
                    results[animal_id] = {
                        'exists': False,
                        'hasDependencies': False,
                        'canDelete': False,
                        'message': 'Animal no encontrado'
                    }
            
            # Verificación batch ultra-optimizada
            for animal in animals:
                warnings = OptimizedIntegrityChecker.check_integrity_fast(Animals, animal.id)
                total_count = sum(w.dependent_count for w in warnings)
                can_delete = all(w.cascade_delete for w in warnings)
                
                results[animal.id] = {
                    'exists': True,
                    'hasDependencies': total_count > 0,
                    'canDelete': can_delete,
                    'totalDependencies': total_count,
                    'message': f"{'Puede eliminarse' if can_delete else 'No puede eliminarse'} ({total_count} dependencias)"
                }
            
            return APIResponse.success(
                data={
                    'results': results,
                    'processed': len(animals),
                    'not_found': len(animal_ids) - len(animals)
                },
                message='Verificación batch completada'
            )
            
        except Exception as e:
            return APIResponse.error(
                message=f'Error en verificación batch: {str(e)}',
                status_code=500
            )

@animals_ns.route('/tree/ancestors')
class AnimalAncestorsTree(Resource):
    @jwt_required()
    def get(self):
        try:
            animal_id = request.args.get('animal_id', type=int)
            if not animal_id:
                return APIResponse.error(message='Parámetro animal_id es requerido', status_code=400)

            max_depth = request.args.get('max_depth', default=5, type=int)
            fields_param = request.args.get('fields')
            fields = [f.strip() for f in fields_param.split(',')] if fields_param else None

            tree = build_ancestor_tree(
                root_id=animal_id,
                max_depth=max_depth,
                fields=fields
            )

            return APIResponse.success(data=tree, message='Árbol de ancestros generado exitosamente')
        except Exception as e:
            return APIResponse.error(message=f'Error al generar árbol de ancestros: {str(e)}')

@animals_ns.route('/tree/descendants')
class AnimalDescendantsTree(Resource):
    @jwt_required()
    def get(self):
        try:
            animal_id = request.args.get('animal_id', type=int)
            if not animal_id:
                return APIResponse.error(message='Parámetro animal_id es requerido', status_code=400)

            max_depth = request.args.get('max_depth', default=5, type=int)
            fields_param = request.args.get('fields')
            fields = [f.strip() for f in fields_param.split(',')] if fields_param else None

            tree = build_descendant_tree(
                root_id=animal_id,
                max_depth=max_depth,
                fields=fields
            )

            return APIResponse.success(data=tree, message='Árbol de descendientes generado exitosamente')
        except Exception as e:
            return APIResponse.error(message=f'Error al generar árbol de descendientes: {str(e)}')

@animals_ns.route('/status')
class AnimalStatus(Resource):
    @jwt_required()
    def get(self):
        try:
            total = Animals.query.count()
            activos = Animals.query.filter(Animals.status == 'Vivo').count()
            inactivos = total - activos
            return APIResponse.success(data={'total': total, 'activos': activos, 'inactivos': inactivos})
        except Exception as e:
            return APIResponse.error(message=f'Error al obtener estadísticas: {str(e)}')