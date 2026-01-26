from flask import request
from flask_restx import Resource, Namespace, fields
import sqlalchemy as sa
from sqlalchemy import and_
from app import db
from flask_jwt_extended import jwt_required, get_jwt_identity

# Asumir que animal_model está definido en modelos o utils
from app.models.animals import Animals
from app.models.animal_images import AnimalImages
from app.utils.response_handler import APIResponse
from app.utils.cache_utils import safe_cached
from app.utils.namespace_helpers import create_optimized_namespace, _cache_clear
from app.utils.tree_builder import build_ancestor_tree, build_descendant_tree, invalidate_animal_tree_cache_for
from app.utils.integrity_checker import OptimizedIntegrityChecker
from app.utils.file_storage import delete_animal_image, delete_animal_directory
from app.models.animalFields import AnimalFields
from datetime import date

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
})

# Note: Standard CRUD, dependencies, and batch checking are now handled by create_optimized_namespace
# custom routes like tree and status are kept below.

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
    @safe_cached(timeout=60, key_prefix='animals_status_stats')
    def get(self):
        try:
            rows = (
                db.session.query(Animals.status, sa.func.count(Animals.id))
                .group_by(Animals.status)
                .all()
            )
            total = sum(cnt for _status, cnt in rows)
            activos = 0
            try:
                from app.models.animals import AnimalStatus as AnimalStatusEnum
                for status, cnt in rows:
                    if str(status) == str(AnimalStatusEnum.Vivo) or status == 'Vivo':
                        activos = cnt
                        break
            except Exception:
                for status, cnt in rows:
                    if status == 'Vivo':
                        activos = cnt
                        break
            inactivos = total - activos
            return APIResponse.success(data={'total': total, 'activos': activos, 'inactivos': inactivos})
        except Exception as e:
            return APIResponse.error(message=f'Error al obtener estadísticas: {str(e)}')
