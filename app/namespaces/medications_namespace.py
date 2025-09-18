# app/namespaces/medications_namespace.py

from flask import request
from flask_restx import Resource, fields
from flask_jwt_extended import jwt_required
# from sqlalchemy.orm import selectinload
from app.models.medications import Medications
from app.models.route_administration import RouteAdministration
from app.utils.namespace_helpers import create_optimized_namespace
from app.utils.response_handler import APIResponse, ResponseFormatter

# Create the optimized namespace for the Medications model
medications_ns = create_optimized_namespace(
    'medications',
    '💊 Gestión de Medicamentos',
    Medications
)

# Enhanced model definitions for Swagger documentation
medication_model = medications_ns.model('Medication', {
    'id': fields.Integer(readOnly=True, description='ID único del medicamento'),
    'name': fields.String(required=True, description='Nombre del medicamento', example='Antibiótico XYZ'),
    'description': fields.String(required=True, description='Descripción del medicamento'),
    'indications': fields.String(required=True, description='Indicaciones del medicamento'),
    'contraindications': fields.String(description='Contraindicaciones del medicamento'),
    'route_administration_id': fields.Integer(required=True, description='ID de la ruta de administración'),
    'availability': fields.Boolean(description='Disponibilidad del medicamento', default=True),
    'created_at': fields.DateTime(readOnly=True, description='Fecha de creación'),
    'updated_at': fields.DateTime(readOnly=True, description='Fecha de última actualización'),
    'route_administration_rel': fields.Nested(medications_ns.model('RouteAdminRef', {
        'id': fields.Integer(description='ID de la ruta de administración'),
        'name': fields.String(description='Nombre de la ruta de administración')
    }), description='Información de la ruta de administración')
})

medication_input_model = medications_ns.model('MedicationInput', {
    'name': fields.String(required=True, description='Nombre del medicamento', example='Antibiótico XYZ'),
    'description': fields.String(required=True, description='Descripción del medicamento'),
    'indications': fields.String(required=True, description='Indicaciones del medicamento'),
    'contraindications': fields.String(description='Contraindicaciones del medicamento'),
    'route_administration_id': fields.Integer(required=True, description='ID de la ruta de administración'),
    'availability': fields.Boolean(description='Disponibilidad del medicamento', default=True)
})

# ---- Legacy custom list endpoints disabled (migrated to generic helper) ----
'''
@medications_ns.route('/with-route-administration')
class MedicationsWithRouteAdmin(Resource):
    @jwt_required()
    @medications_ns.doc('get_medications_with_route_administration', description='Obtener medicamentos con info de ruta (paginado)')
    def get(self):
        page = request.args.get('page', default=1, type=int) or 1
        limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50
        query = Medications.query.options(selectinload(Medications.route_administration_rel))
        pagination = query.paginate(page=page, per_page=int(limit), error_out=False)
        items = [
            (m.to_namespace_dict(include_relations=True) if hasattr(m, 'to_namespace_dict') else {
                'id': m.id,
                'name': m.name,
                'description': m.description,
                'indications': m.indications,
                'contraindications': getattr(m, 'contraindications', None),
                'route_administration_id': m.route_administration_id,
                'availability': getattr(m, 'availability', None),
                'created_at': getattr(m, 'created_at', None),
                'updated_at': getattr(m, 'updated_at', None),
                'route_administration_rel': (
                    m.route_administration_rel.to_namespace_dict() if hasattr(getattr(m, 'route_administration_rel', None), 'to_namespace_dict') else (
                        {
                            'id': getattr(getattr(m, 'route_administration_rel', None), 'id', None),
                            'name': getattr(getattr(m, 'route_administration_rel', None), 'name', None)
                        } if getattr(m, 'route_administration_rel', None) else None
                    )
                )
            }) for m in pagination.items
        ]
        sanitized = ResponseFormatter.sanitize_for_frontend(items)
        return APIResponse.paginated_success(
            data=sanitized,
            page=page,
            limit=int(limit),
            total_items=pagination.total,
            message='Medicamentos con ruta obtenidos'
        )

@medications_ns.route('/by-route/<int:route_id>')
class MedicationsByRoute(Resource):
    @jwt_required()
    @medications_ns.doc('get_medications_by_route', description='Obtener medicamentos por ruta de administración (paginado)')
    def get(self, route_id):
        page = request.args.get('page', default=1, type=int) or 1
        limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50
        query = Medications.query.filter_by(route_administration_id=route_id)
        pagination = query.paginate(page=page, per_page=int(limit), error_out=False)
        items = [
            (m.to_namespace_dict() if hasattr(m, 'to_namespace_dict') else {
                'id': m.id,
                'name': m.name,
                'description': m.description,
                'indications': m.indications,
                'contraindications': getattr(m, 'contraindications', None),
                'route_administration_id': m.route_administration_id,
                'availability': getattr(m, 'availability', None),
                'created_at': getattr(m, 'created_at', None),
                'updated_at': getattr(m, 'updated_at', None)
            }) for m in pagination.items
        ]
        sanitized = ResponseFormatter.sanitize_for_frontend(items)
        return APIResponse.paginated_success(
            data=sanitized,
            page=page,
            limit=int(limit),
            total_items=pagination.total,
            message='Medicamentos por ruta obtenidos'
        )
'''
# --------------------------------------------------------------------------
