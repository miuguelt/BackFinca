from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, extract, desc, literal, and_
from datetime import datetime, timedelta, timezone
import logging
import decimal

from app import db
from app.models.animals import Animals, AnimalStatus, Sex
from app.models.treatments import Treatments
from app.models.vaccinations import Vaccinations
from app.models.control import Control, HealthStatus
from app.models.user import User
from app.models.breeds import Breeds
from app.models.diseases import Diseases
from app.models.medications import Medications
from app.models.vaccines import Vaccines
from app.models.species import Species

from app.utils.response_handler import APIResponse
from app.utils.cache_utils import safe_cached

analytics_ns = Namespace(
    'analytics',
    description='📊 Analytics y Dashboard - Sistema de Gestión Integral',
    path='/analytics'
)

logger = logging.getLogger(__name__)


def calculate_percentage_change(current_value, previous_value, cap=999.0):
    """Calcula variaciones porcentuales controlando desbordes por bases muy pequeñas."""
    current = current_value or 0
    previous = previous_value or 0

    if previous == 0:
        return 100.0 if current > 0 else 0.0

    try:
        change = ((current - previous) / previous) * 100
    except Exception:
        return 0.0

    if cap is not None:
        max_change = float(cap)
        if change > max_change:
            change = max_change
        elif change < -max_change:
            change = -max_change

    return round(change, 1)


def safe_percentage(part, whole, precision=1):
    """Calcula porcentajes evitando divisiones por cero."""
    if not whole:
        return 0.0
    try:
        return round((part / whole) * 100, precision)
    except Exception:
        return 0.0


def percentage_point_delta(current_value, previous_value):
    """Diferencia en puntos porcentuales o valores directos entre periodos."""
    current = current_value or 0
    previous = previous_value or 0
    return round(current - previous, 1)


def build_kpi_cards(context):
    """Genera las tarjetas KPI utilizadas por el dashboard del frontend."""
    window_days = context.get('window_days', 30)
    active_animals = context.get('active_animals') or 0
    total_animals = context.get('total_animals') or 0
    cards = []

    def create_card(card_id, title, value, previous, unit, description, icon, extra=None):
        cards.append({
            'id': card_id,
            'titulo': title,
            'valor': round(value, 2) if isinstance(value, float) else value,
            'unidad': unit,
            'cambio': percentage_point_delta(value, previous),
            'tendencia': {
                'periodo_actual': round(value, 2),
                'periodo_anterior': round(previous, 2),
                'ventana_dias': window_days
            },
            'descripcion': description,
            'icono': icon,
            'detalle': extra or {}
        })

    # Índice de salud general (animales con estado Sano/Bueno/Excelente)
    health_stats = context.get('health_status_stats') or {}
    healthy_animals = sum(health_stats.get(key, 0) for key in ('excelente', 'bueno', 'sano'))
    previous_healthy = max(active_animals - (context.get('animals_critical_health_prev') or 0), 0)
    health_value = safe_percentage(healthy_animals, active_animals)
    health_previous = safe_percentage(previous_healthy, active_animals)
    create_card(
        'health_index',
        'Índice de salud del hato',
        health_value,
        health_previous,
        '%',
        'Porcentaje de animales evaluados como Sano/Bueno/Excelente en los últimos controles.',
        'heart-pulse',
        {
            'animales_saludables': healthy_animals,
            'animales_criticos': context.get('animals_critical_health', 0),
            'total_activos': active_animals
        }
    )

    # Cumplimiento de vacunación (animales vacunados últimos 6 meses)
    animals_without_vaccination = context.get('animals_without_vaccination') or 0
    animals_without_vaccination_prev = context.get('animals_without_vaccination_prev') or 0
    vaccination_value = max(0.0, 100.0 - safe_percentage(animals_without_vaccination, active_animals))
    vaccination_previous = max(0.0, 100.0 - safe_percentage(animals_without_vaccination_prev, active_animals))
    create_card(
        'vaccination_coverage',
        'Cobertura de vacunación',
        vaccination_value,
        vaccination_previous,
        '%',
        'Animales con esquemas de vacunación actualizados (≤ 6 meses).',
        'shield-check',
        {
            'pendientes': animals_without_vaccination,
            'pendientes_prev': animals_without_vaccination_prev
        }
    )

    # Cumplimiento de controles (animales con control < 30 días)
    animals_without_control = context.get('animals_without_control') or 0
    animals_without_control_prev = context.get('animals_without_control_prev') or 0
    control_value = max(0.0, 100.0 - safe_percentage(animals_without_control, active_animals))
    control_previous = max(0.0, 100.0 - safe_percentage(animals_without_control_prev, active_animals))
    create_card(
        'control_compliance',
        'Cumplimiento de controles',
        control_value,
        control_previous,
        '%',
        'Porcentaje de animales con chequeo veterinario en los últimos 30 días.',
        'stethoscope',
        {
            'sin_control': animals_without_control,
            'sin_control_prev': animals_without_control_prev
        }
    )

    # Mortalidad y ventas (últimos 30 días)
    recent_deaths = context.get('recent_deaths') or 0
    recent_deaths_previous = context.get('recent_deaths_previous') or 0
    mortality_value = safe_percentage(recent_deaths, total_animals)
    mortality_previous = safe_percentage(recent_deaths_previous, total_animals)
    create_card(
        'mortality_rate_30d',
        'Tasa de mortalidad 30d',
        mortality_value,
        mortality_previous,
        '%',
        'Bajas registradas en los últimos 30 días sobre el total del hato.',
        'skull',
        {
            'muertes_30d': recent_deaths,
            'muertes_previas': recent_deaths_previous
        }
    )

    recent_sales = context.get('recent_sales') or 0
    recent_sales_previous = context.get('recent_sales_previous') or 0
    sales_value = safe_percentage(recent_sales, total_animals)
    sales_previous = safe_percentage(recent_sales_previous, total_animals)
    create_card(
        'sales_rate_30d',
        'Tasa de ventas 30d',
        sales_value,
        sales_previous,
        '%',
        'Animales marcados como vendidos durante los últimos 30 días.',
        'shopping-cart',
        {
            'ventas_30d': recent_sales,
            'ventas_previas': recent_sales_previous
        }
    )

    # Intensidad de tratamientos y controles
    avg_treatments = context.get('avg_treatments_per_animal') or 0
    avg_treatments_prev = context.get('avg_treatments_per_animal_prev') or 0
    create_card(
        'treatments_intensity',
        'Intensidad de tratamientos',
        avg_treatments,
        avg_treatments_prev,
        'tratamientos/animal',
        'Promedio de tratamientos iniciados por animal en los últimos 30 días.',
        'pill',
        {
            'tratamientos_activos': context.get('active_treatments', 0),
            'tratamientos_previos': context.get('active_treatments_previous', 0)
        }
    )

    avg_controls = context.get('avg_controls_per_animal') or 0
    avg_controls_prev = context.get('avg_controls_per_animal_prev') or 0
    create_card(
        'controls_frequency',
        'Frecuencia de controles',
        avg_controls,
        avg_controls_prev,
        'controles/animal',
        'Controles clínicos realizados por animal en los últimos 30 días.',
        'clipboard-check',
        {
            'controles_30d': context.get('recent_controls_count', 0),
            'controles_previos': context.get('recent_controls_previous', 0)
        }
    )

    # Crecimiento del hato (altas recientes)
    recent_animals = context.get('recent_animals') or 0
    new_animals_previous_period = context.get('new_animals_previous_period') or 0
    herd_growth_value = safe_percentage(recent_animals, total_animals)
    herd_growth_previous = safe_percentage(new_animals_previous_period, total_animals)
    create_card(
        'herd_growth_rate',
        'Crecimiento del hato 30d',
        herd_growth_value,
        herd_growth_previous,
        '%',
        'Ingreso de nuevos animales respecto al tamaño total del hato.',
        'trending-up',
        {
            'altas_30d': recent_animals,
            'altas_previas': new_animals_previous_period
        }
    )

    # Presión de alertas (alertas vs animales activos)
    total_alerts = context.get('total_alerts') or 0
    total_alerts_previous = context.get('total_alerts_previous') or 0
    alert_pressure_value = safe_percentage(total_alerts, active_animals)
    alert_pressure_previous = safe_percentage(total_alerts_previous, active_animals)
    create_card(
        'alert_pressure',
        'Presión de alertas',
        alert_pressure_value,
        alert_pressure_previous,
        '%',
        'Alertas activas comparadas con el número de animales en seguimiento.',
        'alert-triangle',
        {
            'alertas_actuales': total_alerts,
            'alertas_previas': total_alerts_previous
        }
    )

    # Carga operativa (tareas pendientes frente a animales activos)
    pending_tasks = context.get('pending_tasks') or 0
    pending_tasks_previous = context.get('pending_tasks_previous') or 0
    task_load_value = safe_percentage(pending_tasks, active_animals) if active_animals else pending_tasks
    task_load_previous = safe_percentage(pending_tasks_previous, active_animals) if active_animals else pending_tasks_previous
    create_card(
        'task_load_index',
        'Índice de carga operativa',
        task_load_value,
        task_load_previous,
        '%' if active_animals else 'tareas',
        'Relación de tareas pendientes frente a la capacidad del hato activo.',
        'list-checks',
        {
            'tareas_pendientes': pending_tasks,
            'tareas_previas': pending_tasks_previous
        }
    )

    return cards

# Modelos de respuesta
dashboard_model = analytics_ns.model('Dashboard', {
    'total_animals': fields.Integer(description='Total de animales'),
    'active_animals': fields.Integer(description='Animales activos'),
    'health_alerts': fields.Integer(description='Alertas de salud'),
    'productivity_score': fields.Float(description='Puntuación de productividad'),
    'recent_activities': fields.List(fields.Raw, description='Actividades recientes'),
    'generated_at': fields.DateTime(description='Fecha de generación')
})

alerts_model = analytics_ns.model('Alerts', {
    'alerts': fields.List(fields.Raw, description='Lista de alertas'),
    'statistics': fields.Raw(description='Estadísticas de alertas'),
    'generated_at': fields.DateTime(description='Fecha de generación'),
    'filters_applied': fields.Raw(description='Filtros aplicados')
})

custom_report_model = analytics_ns.model('CustomReport', {
    'report': fields.Raw(description='Datos del informe'),
    'metadata': fields.Raw(description='Metadatos del informe')
})

medical_history_model = analytics_ns.model('MedicalHistory', {
    'animal_info': fields.Raw(description='Información del animal'),
    'summary': fields.Raw(description='Resumen médico'),
    'timeline': fields.List(fields.Raw, description='Línea de tiempo médica'),
    'treatments': fields.List(fields.Raw, description='Tratamientos'),
    'vaccinations': fields.List(fields.Raw, description='Vacunaciones'),
    'controls': fields.List(fields.Raw, description='Controles'),
    'alerts': fields.List(fields.Raw, description='Alertas')
})

production_stats_model = analytics_ns.model('ProductionStats', {
    'weight_trends': fields.List(fields.Raw, description='Tendencias de peso'),
    'growth_rates': fields.List(fields.Raw, description='Tasas de crecimiento'),
    'productivity_metrics': fields.Raw(description='Métricas de productividad'),
    'best_performers': fields.List(fields.Raw, description='Mejores performers'),
    'group_statistics': fields.Raw(description='Estadísticas por grupo'),
    'summary': fields.Raw(description='Resumen')
})

animal_stats_model = analytics_ns.model('AnimalStats', {
    'by_status': fields.Raw(description='Por estado'),
    'by_sex': fields.Raw(description='Por sexo'),
    'by_breed': fields.List(fields.Raw, description='Por raza'),
    'by_age_group': fields.Raw(description='Por grupo de edad'),
    'weight_distribution': fields.Raw(description='Distribución de pesos'),
    'total_animals': fields.Integer(description='Total de animales'),
    'average_weight': fields.Float(description='Peso promedio')
})

health_stats_model = analytics_ns.model('HealthStats', {
    'treatments_by_month': fields.List(fields.Raw, description='Tratamientos por mes'),
    'vaccinations_by_month': fields.List(fields.Raw, description='Vacunaciones por mes'),
    'health_status_distribution': fields.Raw(description='Distribución de estados de salud'),
    'common_diseases': fields.List(fields.Raw, description='Enfermedades comunes'),
    'medication_usage': fields.List(fields.Raw, description='Uso de medicamentos'),
    'summary': fields.Raw(description='Resumen')
})

@analytics_ns.route('/dashboard')
class DashboardStats(Resource):
    @analytics_ns.doc(
        'get_dashboard_stats',
        description='''
        **Estadísticas principales del dashboard**

        Retorna un resumen completo de las métricas clave del sistema:
        - Total de animales y distribución por estado
        - Actividad médica (tratamientos y vacunaciones)
        - Usuarios del sistema
        - Actividades recientes

        **Casos de uso:**
        - Dashboard principal de la aplicación
        - Vista general del estado de la finca
        - Métricas para toma de decisiones
        ''',
        security=['Bearer', 'Cookie'],
        responses={
            200: ('Estadísticas del dashboard', dashboard_model),
            401: 'Token JWT requerido o inválido',
            500: 'Error interno del servidor'
        }
    )
    @jwt_required()
    def get(self):
        """Obtener estadísticas principales del dashboard"""
        try:
            # Inicio obtención de estadísticas de dashboard

            # Animal Stats
            animals_stats = Animals.get_stats()

            # Health Stats
            treatments_stats = Treatments.get_stats()
            vaccinations_stats = Vaccinations.get_stats()
            control_stats = Control.get_stats()

            # User Stats
            users_stats = User.get_stats()

            dashboard_data = {
                'total_animals': animals_stats.get('total_count', 0),
                'active_animals': animals_stats.get('active_count', 0),
                'animals_by_status': animals_stats.get('status_distribution', {}),
                'animals_by_sex': animals_stats.get('sex_distribution', {}),
                'average_weight': animals_stats.get('average_weight', 0),
                'total_treatments': treatments_stats.get('total_count', 0),
                'recent_treatments_week': treatments_stats.get('recent_additions', 0),
                'total_vaccinations': vaccinations_stats.get('total_count', 0),
                'recent_vaccinations_week': vaccinations_stats.get('recent_additions', 0),
                'total_controls': control_stats.get('total_count', 0),
                'health_summary': control_stats.get('health_status_distribution', {}),
                'total_users': users_stats.get('total_count', 0),
                'active_users': users_stats.get('active_count', 0),
            }

            return APIResponse.success(dashboard_data, "Estadísticas del dashboard obtenidas exitosamente")

        except Exception as e:
            logger.error("Error fetching dashboard stats")
            return APIResponse.error("Error interno del servidor al obtener estadísticas.", status_code=500)

@analytics_ns.route('/dashboard/complete')
class CompleteDashboardStats(Resource):
    @analytics_ns.doc(
        'get_complete_dashboard_stats',
        description='''
        **Estadísticas completas del dashboard optimizadas**

        Retorna TODAS las métricas del sistema calculadas en el backend de forma optimizada:
        - Usuarios registrados y activos
        - Animales registrados y por campo
        - Tratamientos activos y totales
        - Vacunas aplicadas y catálogo
        - Controles realizados
        - Campos registrados
        - Catálogos completos (medicamentos, enfermedades, especies, razas, alimentos)
        - Relaciones (animales por campo/enfermedad)
        - Mejoras genéticas
        - Tareas pendientes y alertas del sistema

        **Optimizaciones aplicadas:**
        - Todas las consultas se ejecutan en paralelo cuando es posible
        - Uso de COUNT() y agregaciones en lugar de traer todos los datos
        - Caché automático de 2 minutos
        - Una sola llamada al backend para obtener todas las estadísticas

        **Casos de uso:**
        - Dashboard principal de la aplicación
        - Vista general completa del estado de la finca
        - Métricas para toma de decisiones
        - Reducción de llamadas HTTP desde el frontend
        ''',
        security=['Bearer', 'Cookie'],
        responses={
            200: 'Estadísticas completas del dashboard',
            401: 'Token JWT requerido o inválido',
            500: 'Error interno del servidor'
        }
    )
    @jwt_required()
    @safe_cached(timeout=120, key_prefix='dashboard_complete_stats')
    def get(self):
        """Obtener estadísticas completas del dashboard con máxima optimización"""
        try:
            from app.models.animalFields import AnimalFields
            from app.models.animalDiseases import AnimalDiseases
            from app.models.geneticImprovements import GeneticImprovements
            from app.models.treatment_medications import TreatmentMedications
            from app.models.treatment_vaccines import TreatmentVaccines
            from app.models.foodTypes import FoodTypes
            from app.models.fields import Fields
            from datetime import timedelta

            current_date = datetime.now(timezone.utc)
            thirty_days_ago = current_date - timedelta(days=30)
            sixty_days_ago = current_date - timedelta(days=60)
            seven_days_ago = current_date - timedelta(days=7)
            # Fechas normalizadas para columnas tipo Date
            current_date_date = current_date.date()
            thirty_days_ago_date = thirty_days_ago.date()
            sixty_days_ago_date = sixty_days_ago.date()
            seven_days_ago_date = seven_days_ago.date()
            six_months_ago_date = (current_date - timedelta(days=180)).date()

            # ============================================
            # SECCIÓN 1: USUARIOS
            # ============================================
            # Total de usuarios registrados
            total_users = db.session.query(func.count(User.id)).scalar() or 0

            # Total antes del período actual (estado hace 30 días)
            total_users_before_period = db.session.query(func.count(User.id)).filter(
                User.created_at < thirty_days_ago
            ).scalar() or 0

            # Nuevos usuarios en el período anterior para contexto
            new_users_previous_period = db.session.query(func.count(User.id)).filter(
                and_(
                    User.created_at >= sixty_days_ago,
                    User.created_at < thirty_days_ago
                )
            ).scalar() or 0

            new_users_current_period = total_users - total_users_before_period
            users_change_percentage = calculate_percentage_change(total_users, total_users_before_period)

            # Usuarios activos (actividad real en los últimos 30 días)
            active_users = db.session.query(func.count(User.id)).filter(
                User.updated_at >= thirty_days_ago
            ).scalar() or 0

            # Usuarios activos del período anterior (30-60 días atrás)
            active_users_previous = db.session.query(func.count(User.id)).filter(
                and_(
                    User.updated_at >= sixty_days_ago,
                    User.updated_at < thirty_days_ago
                )
            ).scalar() or 0

            active_users_change_percentage = calculate_percentage_change(active_users, active_users_previous)

            # ============================================
            # SECCIÓN 2: ANIMALES
            # ============================================
            # Total de animales registrados
            total_animals = db.session.query(func.count(Animals.id)).scalar() or 0

            # Total antes del período actual y altas recientes
            total_animals_before_period = db.session.query(func.count(Animals.id)).filter(
                Animals.created_at < thirty_days_ago
            ).scalar() or 0
            new_animals_previous_period = db.session.query(func.count(Animals.id)).filter(
                and_(
                    Animals.created_at >= sixty_days_ago,
                    Animals.created_at < thirty_days_ago
                )
            ).scalar() or 0

            recent_animals = total_animals - total_animals_before_period
            animals_change_percentage = calculate_percentage_change(total_animals, total_animals_before_period)

            # Animales activos/vivos
            active_animals = db.session.query(func.count(Animals.id)).filter(
                Animals.status == AnimalStatus.Vivo
            ).scalar() or 0

            # ============================================
            # SECCIÓN 3: TRATAMIENTOS
            # ============================================
            # Total de tratamientos históricos
            total_treatments = db.session.query(func.count(Treatments.id)).scalar() or 0

            treatments_before_period = db.session.query(func.count(Treatments.id)).filter(
                Treatments.created_at < thirty_days_ago
            ).scalar() or 0
            treatments_previous_period = db.session.query(func.count(Treatments.id)).filter(
                and_(
                    Treatments.created_at >= sixty_days_ago,
                    Treatments.created_at < thirty_days_ago
                )
            ).scalar() or 0
            treatments_current_period = total_treatments - treatments_before_period
            treatments_change_percentage = calculate_percentage_change(total_treatments, treatments_before_period)

            # Tratamientos activos (en curso - últimos 30 días)
            active_treatments = db.session.query(func.count(Treatments.id)).filter(
                Treatments.treatment_date >= thirty_days_ago_date
            ).scalar() or 0

            # Tratamientos activos del período anterior (30-60 días atrás)
            active_treatments_previous = db.session.query(func.count(Treatments.id)).filter(
                and_(
                    Treatments.treatment_date >= sixty_days_ago_date,
                    Treatments.treatment_date < thirty_days_ago_date
                )
            ).scalar() or 0

            # Tratamientos recientes
            recent_treatments = db.session.query(func.count(Treatments.id)).filter(
                Treatments.created_at >= seven_days_ago
            ).scalar() or 0

            # ============================================
            # SECCIÓN 4: VACUNAS
            # ============================================
            # Total de vacunaciones aplicadas
            total_vaccinations = db.session.query(func.count(Vaccinations.id)).scalar() or 0

            vaccinations_before_period = db.session.query(func.count(Vaccinations.id)).filter(
                Vaccinations.vaccination_date < thirty_days_ago_date
            ).scalar() or 0
            vaccinations_previous_period = db.session.query(func.count(Vaccinations.id)).filter(
                and_(
                    Vaccinations.vaccination_date >= sixty_days_ago_date,
                    Vaccinations.vaccination_date < thirty_days_ago_date
                )
            ).scalar() or 0
            vaccinations_current_period = total_vaccinations - vaccinations_before_period
            vaccinations_change_percentage = calculate_percentage_change(total_vaccinations, vaccinations_before_period)

            # Vacunaciones recientes
            recent_vaccinations = db.session.query(func.count(Vaccinations.id)).filter(
                Vaccinations.vaccination_date >= seven_days_ago_date
            ).scalar() or 0

            # ============================================
            # SECCIÓN 5: CONTROLES
            # ============================================
            # Total de controles de salud realizados
            total_controls = db.session.query(func.count(Control.id)).scalar() or 0

            controls_before_period = db.session.query(func.count(Control.id)).filter(
                Control.checkup_date < thirty_days_ago_date
            ).scalar() or 0
            controls_previous_period = db.session.query(func.count(Control.id)).filter(
                and_(
                    Control.checkup_date >= sixty_days_ago_date,
                    Control.checkup_date < thirty_days_ago_date
                )
            ).scalar() or 0
            controls_current_period = total_controls - controls_before_period
            controls_change_percentage = calculate_percentage_change(total_controls, controls_before_period)

            # Controles recientes
            recent_controls = db.session.query(func.count(Control.id)).filter(
                Control.checkup_date >= seven_days_ago_date
            ).scalar() or 0

            # Controles del período anterior (30-60 días atrás)
            recent_controls_previous = db.session.query(func.count(Control.id)).filter(
                and_(
                    Control.checkup_date >= sixty_days_ago_date,
                    Control.checkup_date < thirty_days_ago_date
                )
            ).scalar() or 0

            # ============================================
            # SECCIÓN 6: CAMPOS/LOTES
            # ============================================
            total_fields = db.session.query(func.count(Fields.id)).scalar() or 0

            fields_before_period = db.session.query(func.count(Fields.id)).filter(
                Fields.created_at < thirty_days_ago
            ).scalar() or 0
            fields_previous_period = db.session.query(func.count(Fields.id)).filter(
                and_(
                    Fields.created_at >= sixty_days_ago,
                    Fields.created_at < thirty_days_ago
                )
            ).scalar() or 0
            fields_current_period = total_fields - fields_before_period
            fields_change_percentage = calculate_percentage_change(total_fields, fields_before_period)

            # ============================================
            # SECCIÓN 7: CATÁLOGOS
            # ============================================
            # Catálogo de vacunas disponibles
            total_vaccines_catalog = db.session.query(func.count(Vaccines.id)).scalar() or 0

            # Catálogo de medicamentos
            total_medications_catalog = db.session.query(func.count(Medications.id)).scalar() or 0

            # Catálogo de enfermedades
            total_diseases_catalog = db.session.query(func.count(Diseases.id)).scalar() or 0

            # Catálogo de especies
            total_species_catalog = db.session.query(func.count(Species.id)).scalar() or 0

            # Catálogo de razas
            total_breeds_catalog = db.session.query(func.count(Breeds.id)).scalar() or 0

            # Catálogo de tipos de alimento
            total_food_types_catalog = db.session.query(func.count(FoodTypes.id)).scalar() or 0

            # ============================================
            # SECCIÓN 8: RELACIONES
            # ============================================
            # Animales por campo (relaciones Animal-Campo)
            total_animal_fields = db.session.query(func.count(AnimalFields.id)).scalar() or 0

            # Animales por enfermedad (relaciones Animal-Enfermedad)
            total_animal_diseases = db.session.query(func.count(AnimalDiseases.id)).scalar() or 0

            # ============================================
            # SECCIÓN 9: MEJORAS GENÉTICAS
            # ============================================
            total_genetic_improvements = db.session.query(func.count(GeneticImprovements.id)).scalar() or 0

            # ============================================
            # SECCIÓN 10: TRATAMIENTOS CON MEDICAMENTOS Y VACUNAS
            # ============================================
            # Tratamientos con medicamentos
            total_treatment_medications = db.session.query(func.count(TreatmentMedications.id)).scalar() or 0

            # Tratamientos con vacunas
            total_treatment_vaccines = db.session.query(func.count(TreatmentVaccines.id)).scalar() or 0

            # ============================================
            # SECCIÓN 11: ALERTAS Y TAREAS
            # ============================================
            # Para las alertas, vamos a contar diferentes tipos de alertas
            # Animales sin control reciente (>30 días)
            animals_without_control = db.session.query(func.count(Animals.id)).filter(
                Animals.status == AnimalStatus.Vivo,
                ~Animals.id.in_(
                    db.session.query(Control.animal_id).filter(
                        Control.checkup_date >= thirty_days_ago_date
                    )
                )
            ).scalar() or 0

            # Animales sin vacunación reciente (>180 días)
            animals_without_vaccination = db.session.query(func.count(Animals.id)).filter(
                Animals.status == AnimalStatus.Vivo,
                ~Animals.id.in_(
                    db.session.query(Vaccinations.animal_id).filter(
                        Vaccinations.vaccination_date >= six_months_ago_date
                    )
                )
            ).scalar() or 0

            # Animales con estado de salud crítico
            animals_critical_health = db.session.query(
                func.count(func.distinct(Control.animal_id))
            ).join(Animals).filter(
                Animals.status == AnimalStatus.Vivo,
                Control.health_status.in_([HealthStatus.Malo, HealthStatus.Regular]),
                Control.checkup_date >= thirty_days_ago_date
            ).scalar() or 0

            # Total de alertas del sistema
            total_alerts = animals_without_control + animals_without_vaccination + animals_critical_health

            # Calcular alertas del período anterior para obtener el cambio porcentual
            # Animales sin control del período anterior (30-60 días atrás)
            animals_without_control_prev = db.session.query(func.count(Animals.id)).filter(
                Animals.status == AnimalStatus.Vivo,
                ~Animals.id.in_(
                    db.session.query(Control.animal_id).filter(
                        and_(
                            Control.checkup_date >= sixty_days_ago_date,
                            Control.checkup_date < thirty_days_ago_date
                        )
                    )
                )
            ).scalar() or 0

            # Animales sin vacunación del período anterior
            animals_without_vaccination_prev = db.session.query(func.count(Animals.id)).filter(
                Animals.status == AnimalStatus.Vivo,
                ~Animals.id.in_(
                    db.session.query(Vaccinations.animal_id).filter(
                        and_(
                            Vaccinations.vaccination_date >= (current_date_date - timedelta(days=210)),  # 180 + 30 días
                            Vaccinations.vaccination_date < six_months_ago_date
                        )
                    )
                )
            ).scalar() or 0

            # Animales con estado crítico del período anterior
            animals_critical_health_prev = db.session.query(
                func.count(func.distinct(Control.animal_id))
            ).join(Animals).filter(
                Animals.status == AnimalStatus.Vivo,
                Control.health_status.in_([HealthStatus.Malo, HealthStatus.Regular]),
                and_(
                    Control.checkup_date >= sixty_days_ago_date,
                    Control.checkup_date < thirty_days_ago_date
                )
            ).scalar() or 0

            total_alerts_previous = animals_without_control_prev + animals_without_vaccination_prev + animals_critical_health_prev

            # Calcular porcentaje de cambio en alertas
            if total_alerts_previous > 0:
                alerts_change_percentage = round(((total_alerts - total_alerts_previous) / total_alerts_previous) * 100, 1)
            else:
                alerts_change_percentage = 0

            # Tareas pendientes
            # Consideramos tareas pendientes como:
            # - Animales que necesitan control
            # - Animales que necesitan vacunación
            # - Tratamientos activos
            pending_tasks = animals_without_control + animals_without_vaccination + active_treatments

            pending_tasks_previous = animals_without_control_prev + animals_without_vaccination_prev + active_treatments_previous

            # Calcular porcentaje de cambio en tareas pendientes
            if pending_tasks_previous > 0:
                tasks_change_percentage = round(((pending_tasks - pending_tasks_previous) / pending_tasks_previous) * 100, 1)
            else:
                tasks_change_percentage = 0

            # ============================================
            # SECCIÓN 12: ESTADÍSTICAS ADICIONALES CALCULADAS
            # ============================================

            # Distribución de animales por sexo
            animals_by_sex = db.session.query(
                Animals.sex,
                func.count(Animals.id).label('count')
            ).filter(
                Animals.status == AnimalStatus.Vivo
            ).group_by(Animals.sex).all()

            sex_distribution = {
                'machos': next((count for sex, count in animals_by_sex if sex == Sex.Macho), 0),
                'hembras': next((count for sex, count in animals_by_sex if sex == Sex.Hembra), 0)
            }

            # Distribución de animales por raza (top 5)
            animals_by_breed = db.session.query(
                Breeds.name,
                func.count(Animals.id).label('count')
            ).join(Animals).filter(
                Animals.status == AnimalStatus.Vivo
            ).group_by(Breeds.name).order_by(
                desc(func.count(Animals.id))
            ).limit(5).all()

            breed_distribution = [
                {'raza': breed, 'cantidad': count}
                for breed, count in animals_by_breed
            ]

            # Distribución de animales por estado
            animals_by_status = db.session.query(
                Animals.status,
                func.count(Animals.id).label('count')
            ).group_by(Animals.status).all()

            status_distribution = {
                'vivos': next((count for status, count in animals_by_status if status == AnimalStatus.Vivo), 0),
                'vendidos': next((count for status, count in animals_by_status if status == AnimalStatus.Vendido), 0),
                'muertos': next((count for status, count in animals_by_status if status == AnimalStatus.Muerto), 0)
            }

            # Peso promedio de animales activos
            avg_weight = db.session.query(
                func.avg(Animals.weight)
            ).filter(
                Animals.status == AnimalStatus.Vivo
            ).scalar() or 0

            if isinstance(avg_weight, decimal.Decimal):
                avg_weight = float(avg_weight)

            # Distribución de estado de salud (últimos controles)
            # Obtener el último control de cada animal
            latest_controls = db.session.query(
                Control.animal_id,
                Control.health_status,
                func.max(Control.checkup_date).label('last_checkup')
            ).join(Animals).filter(
                Animals.status == AnimalStatus.Vivo
            ).group_by(
                Control.animal_id,
                Control.health_status
            ).subquery()

            health_distribution = db.session.query(
                latest_controls.c.health_status,
                func.count(latest_controls.c.animal_id).label('count')
            ).group_by(latest_controls.c.health_status).all()

            health_status_stats = {
                'excelente': next((count for status, count in health_distribution if status == HealthStatus.Excelente), 0),
                'bueno': next((count for status, count in health_distribution if status == HealthStatus.Bueno), 0),
                'sano': next((count for status, count in health_distribution if status == HealthStatus.Sano), 0),
                'regular': next((count for status, count in health_distribution if status == HealthStatus.Regular), 0),
                'malo': next((count for status, count in health_distribution if status == HealthStatus.Malo), 0)
            }

            # Grupos de edad de animales
            # Calcular edad en meses para cada animal vivo
            current_date_date = current_date.date() if hasattr(current_date, 'date') else current_date

            age_groups = {
                'terneros': 0,      # 0-12 meses
                'jovenes': 0,       # 12-24 meses
                'adultos': 0,       # 24-60 meses
                'maduros': 0        # 60+ meses
            }

            animals_with_birth = db.session.query(
                Animals.birth_date
            ).filter(
                Animals.status == AnimalStatus.Vivo,
                Animals.birth_date.isnot(None)
            ).all()

            for animal in animals_with_birth:
                if animal.birth_date:
                    age_days = (current_date_date - animal.birth_date).days
                    age_months = age_days / 30.44

                    if age_months < 12:
                        age_groups['terneros'] += 1
                    elif age_months < 24:
                        age_groups['jovenes'] += 1
                    elif age_months < 60:
                        age_groups['adultos'] += 1
                    else:
                        age_groups['maduros'] += 1

            # Tasa de mortalidad (últimos 30 días)
            recent_deaths = db.session.query(func.count(Animals.id)).filter(
                Animals.status == AnimalStatus.Muerto,
                Animals.updated_at >= thirty_days_ago
            ).scalar() or 0

            recent_deaths_previous = db.session.query(func.count(Animals.id)).filter(
                Animals.status == AnimalStatus.Muerto,
                and_(
                    Animals.updated_at >= sixty_days_ago,
                    Animals.updated_at < thirty_days_ago
                )
            ).scalar() or 0

            # Tasa de ventas (últimos 30 días)
            recent_sales = db.session.query(func.count(Animals.id)).filter(
                Animals.status == AnimalStatus.Vendido,
                Animals.updated_at >= thirty_days_ago
            ).scalar() or 0

            recent_sales_previous = db.session.query(func.count(Animals.id)).filter(
                Animals.status == AnimalStatus.Vendido,
                and_(
                    Animals.updated_at >= sixty_days_ago,
                    Animals.updated_at < thirty_days_ago
                )
            ).scalar() or 0

            # Promedio de tratamientos por animal (últimos 30 días)
            if active_animals > 0:
                avg_treatments_per_animal = round(active_treatments / active_animals, 2)
                avg_treatments_previous_avg = round(active_treatments_previous / active_animals, 2)
            else:
                avg_treatments_per_animal = 0
                avg_treatments_previous_avg = 0

            # Promedio de controles por animal (últimos 30 días)
            recent_controls_count = db.session.query(func.count(Control.id)).filter(
                Control.checkup_date >= thirty_days_ago_date
            ).scalar() or 0

            if active_animals > 0:
                avg_controls_per_animal = round(recent_controls_count / active_animals, 2)
                avg_controls_previous_avg = round(recent_controls_previous / active_animals, 2)
            else:
                avg_controls_per_animal = 0
                avg_controls_previous_avg = 0

            # ============================================
            # CONSTRUIR RESPUESTA COMPLETA
            # ============================================
            kpi_cards = build_kpi_cards({
                'total_animals': total_animals,
                'active_animals': active_animals,
                'health_status_stats': health_status_stats,
                'animals_critical_health': animals_critical_health,
                'animals_critical_health_prev': animals_critical_health_prev,
                'animals_without_control': animals_without_control,
                'animals_without_control_prev': animals_without_control_prev,
                'animals_without_vaccination': animals_without_vaccination,
                'animals_without_vaccination_prev': animals_without_vaccination_prev,
                'recent_deaths': recent_deaths,
                'recent_deaths_previous': recent_deaths_previous,
                'recent_sales': recent_sales,
                'recent_sales_previous': recent_sales_previous,
                'avg_treatments_per_animal': avg_treatments_per_animal,
                'avg_treatments_per_animal_prev': avg_treatments_previous_avg,
                'avg_controls_per_animal': avg_controls_per_animal,
                'avg_controls_per_animal_prev': avg_controls_previous_avg,
                'active_treatments': active_treatments,
                'active_treatments_previous': active_treatments_previous,
                'recent_controls_count': recent_controls_count,
                'recent_controls_previous': recent_controls_previous,
                'recent_animals': recent_animals,
                'new_animals_previous_period': new_animals_previous_period,
                'total_alerts': total_alerts,
                'total_alerts_previous': total_alerts_previous,
                'pending_tasks': pending_tasks,
                'pending_tasks_previous': pending_tasks_previous,
                'window_days': 30
            })

            complete_stats = {
                # Usuarios
                'usuarios_registrados': {
                    'valor': total_users,
                    'cambio_porcentual': users_change_percentage,
                    'descripcion': 'Número total de usuarios en el sistema.',
                    'tendencia': {
                        'periodo_actual': new_users_current_period,
                        'periodo_anterior': new_users_previous_period
                    }
                },
                'usuarios_activos': {
                    'valor': active_users,
                    'cambio_porcentual': active_users_change_percentage,
                    'descripcion': 'Usuarios con actividad reciente o sesión activa.',
                    'tendencia': {
                        'periodo_actual': active_users,
                        'periodo_anterior': active_users_previous
                    }
                },

                # Animales
                'animales_registrados': {
                    'valor': total_animals,
                    'cambio_porcentual': animals_change_percentage,
                    'descripcion': 'Total de animales con ficha en la base de datos.',
                    'tendencia': {
                        'periodo_actual': recent_animals,
                        'periodo_anterior': new_animals_previous_period
                    }
                },
                'animales_activos': {
                    'valor': active_animals,
                    'cambio_porcentual': 0,
                    'descripcion': 'Animales vivos en el sistema.'
                },

                # Tratamientos
                'tratamientos_activos': {
                    'valor': active_treatments,
                    'cambio_porcentual': 0,
                    'descripcion': 'Tratamientos actualmente en curso (últimos 30 días).'
                },
                'tratamientos_totales': {
                    'valor': total_treatments,
                    'cambio_porcentual': treatments_change_percentage,
                    'descripcion': 'Cantidad histórica de tratamientos registrados.',
                    'tendencia': {
                        'periodo_actual': treatments_current_period,
                        'periodo_anterior': treatments_previous_period
                    }
                },

                # Tareas y Alertas
                'tareas_pendientes': {
                    'valor': pending_tasks,
                    'cambio_porcentual': tasks_change_percentage,
                    'descripcion': 'Acciones que requieren atención.'
                },
                'alertas_sistema': {
                    'valor': total_alerts,
                    'cambio_porcentual': alerts_change_percentage,
                    'descripcion': 'Notificaciones y advertencias generadas por el sistema.',
                    'desglose': {
                        'animales_sin_control': animals_without_control,
                        'animales_sin_vacunacion': animals_without_vaccination,
                        'estado_salud_critico': animals_critical_health
                    }
                },

                # Vacunas y Controles
                'vacunas_aplicadas': {
                    'valor': total_vaccinations,
                    'cambio_porcentual': vaccinations_change_percentage,
                    'descripcion': 'Vacunaciones registradas en el sistema.',
                    'tendencia': {
                        'periodo_actual': vaccinations_current_period,
                        'periodo_anterior': vaccinations_previous_period
                    }
                },
                'controles_realizados': {
                    'valor': total_controls,
                    'cambio_porcentual': controls_change_percentage,
                    'descripcion': 'Controles de producción/seguimiento ejecutados.',
                    'tendencia': {
                        'periodo_actual': controls_current_period,
                        'periodo_anterior': controls_previous_period
                    }
                },

                # Campos
                'campos_registrados': {
                    'valor': total_fields,
                    'cambio_porcentual': fields_change_percentage,
                    'descripcion': 'Número de lotes/campos administrados.',
                    'tendencia': {
                        'periodo_actual': fields_current_period,
                        'periodo_anterior': fields_previous_period
                    }
                },

                # KPIs derivados
                'kpi_resumen': {
                    'ventana_dias': 30,
                    'cards': kpi_cards
                },

                # Catálogos
                'catalogo_vacunas': {
                    'valor': total_vaccines_catalog,
                    'descripcion': 'Catálogo de vacunas disponibles.'
                },
                'catalogo_medicamentos': {
                    'valor': total_medications_catalog,
                    'descripcion': 'Catálogo de medicamentos registrados.'
                },
                'catalogo_enfermedades': {
                    'valor': total_diseases_catalog,
                    'descripcion': 'Catálogo de enfermedades administradas.'
                },
                'catalogo_especies': {
                    'valor': total_species_catalog,
                    'descripcion': 'Catálogo de especies registradas.'
                },
                'catalogo_razas': {
                    'valor': total_breeds_catalog,
                    'descripcion': 'Catálogo de razas disponibles.'
                },
                'catalogo_tipos_alimento': {
                    'valor': total_food_types_catalog,
                    'descripcion': 'Catálogo de alimentos disponibles.'
                },

                # Relaciones
                'animales_por_campo': {
                    'valor': total_animal_fields,
                    'descripcion': 'Relaciones Animal-Campo registradas.'
                },
                'animales_por_enfermedad': {
                    'valor': total_animal_diseases,
                    'descripcion': 'Relaciones Animal-Enfermedad registradas.'
                },

                # Mejoras genéticas y tratamientos especializados
                'mejoras_geneticas': {
                    'valor': total_genetic_improvements,
                    'descripcion': 'Intervenciones de mejora genética.'
                },
                'tratamientos_con_medicamentos': {
                    'valor': total_treatment_medications,
                    'descripcion': 'Registros de tratamientos con fármacos.'
                },
                'tratamientos_con_vacunas': {
                    'valor': total_treatment_vaccines,
                    'descripcion': 'Registros de tratamientos con vacunas.'
                },

                # ============================================
                # ESTADÍSTICAS ADICIONALES CALCULADAS
                # ============================================
                'distribucion_sexo': sex_distribution,
                'distribucion_razas_top5': breed_distribution,
                'distribucion_estado': status_distribution,
                'peso_promedio_kg': round(avg_weight, 2),
                'distribucion_salud': health_status_stats,
                'grupos_edad': age_groups,
                'muertes_recientes_30dias': recent_deaths,
                'ventas_recientes_30dias': recent_sales,
                'promedio_tratamientos_por_animal': avg_treatments_per_animal,
                'promedio_controles_por_animal': avg_controls_per_animal,

                # Metadata
                'metadata': {
                    'generado_en': current_date.isoformat(),
                    'version': '2.1',
                    'optimizado': True,
                    'cache_ttl': 120,  # segundos
                    'estadisticas_totales': 33  # 23 originales + 10 adicionales
                }
            }

            return APIResponse.success(
                data=complete_stats,
                message="Estadísticas completas del dashboard obtenidas exitosamente"
            )

        except Exception as e:
            logger.error(f"Error obteniendo estadísticas completas del dashboard: {str(e)}")
            return APIResponse.error(
                message="Error interno del servidor al obtener estadísticas completas.",
                status_code=500,
                details={'error': str(e)}
            )

@analytics_ns.route('/alerts')
class SystemAlerts(Resource):
    @analytics_ns.doc(
        'get_system_alerts',
        description='''
        **Sistema de alertas y notificaciones automáticas**
        
        Genera alertas inteligentes basadas en el estado del hato:
        - Animales que requieren atención médica
        - Controles de salud vencidos
        - Vacunaciones pendientes
        - Anomalías en el crecimiento
        - Alertas de productividad
        
        **Parámetros opcionales:**
        - `priority`: Filtrar por prioridad (high, medium, low)
        - `type`: Tipo de alerta (health, vaccination, growth, productivity)
        - `limit`: Número máximo de alertas (default: 50)
        
        **Útil para:**
        - Dashboard de alertas
        - Notificaciones push
        - Planificación de actividades
        ''',
        security=['Bearer', 'Cookie'],
        params={
            'priority': {'description': 'Filtrar por prioridad', 'type': 'string', 'enum': ['high', 'medium', 'low']},
            'type': {'description': 'Tipo de alerta', 'type': 'string', 'enum': ['health', 'vaccination', 'growth', 'productivity']},
            'limit': {'description': 'Número máximo de alertas', 'type': 'integer', 'default': 50}
        },
        responses={
            200: 'Lista de alertas del sistema',
            401: 'Token JWT requerido o inválido',
            500: 'Error interno del servidor'
        }
    )
    @jwt_required()
    def get(self):
        """Obtener alertas y notificaciones del sistema"""
        try:
            priority_filter = request.args.get('priority')
            type_filter = request.args.get('type')
            limit = int(request.args.get('limit', 50))
            
            alerts = []
            current_date = datetime.now().date()
            
            # 1. Alertas de salud - Animales sin control reciente
            if not type_filter or type_filter == 'health':
                thirty_days_ago = current_date - timedelta(days=30)
                
                animals_without_control = db.session.query(
                    Animals.id,
                    Animals.record,
                    func.max(Control.checkup_date).label('last_control')
                ).outerjoin(Control).filter(
                    Animals.status == AnimalStatus.Vivo
                ).group_by(
                    Animals.id, Animals.record
                ).having(
                    func.coalesce(func.max(Control.checkup_date), '1900-01-01') < thirty_days_ago
                ).all()
                
                for animal in animals_without_control:
                    days_without_control = (current_date - (animal.last_control or datetime(1900, 1, 1).date())).days
                    
                    priority = 'high' if days_without_control > 60 else 'medium'
                    
                    alerts.append({
                        'id': f'health_{animal.id}',
                        'type': 'health',
                        'priority': priority,
                        'title': f'Control vencido - {animal.record}',
                        'message': f'Animal sin control hace {days_without_control} días',
                        'animal_id': animal.id,
                        'animal_record': animal.record,
                        'action_required': 'Programar control de salud',
                        'created_at': current_date.isoformat(),
                        'icon': '⚠️',
                        'color': 'orange' if priority == 'medium' else 'red'
                    })
            
            # 2. Alertas de estado de salud crítico
            if not type_filter or type_filter == 'health':
                critical_health = db.session.query(
                    Animals.id,
                    Animals.record,
                    Control.health_status,
                    Control.checkup_date
                ).join(Control).filter(
                    Animals.status == AnimalStatus.Vivo,
                    Control.health_status.in_([HealthStatus.Malo, HealthStatus.Regular]),
                    Control.checkup_date >= current_date - timedelta(days=30)
                ).order_by(desc(Control.checkup_date)).all()
                
                for animal in critical_health:
                    priority = 'high' if animal.health_status == HealthStatus.Malo else 'medium'
                    
                    alerts.append({
                        'id': f'critical_health_{animal.id}',
                        'type': 'health',
                        'priority': priority,
                        'title': f'Estado crítico - {animal.record}',
                        'message': f'Estado de salud: {animal.health_status.value}',
                        'animal_id': animal.id,
                        'animal_record': animal.record,
                        'action_required': 'Evaluación veterinaria urgente',
                        'created_at': animal.checkup_date.isoformat() if getattr(animal, 'checkup_date', None) else current_date.isoformat(),
                        'icon': '🚨',
                        'color': 'red'
                    })
            
            # 3. Alertas de vacunación - Animales que necesitan vacunas
            if not type_filter or type_filter == 'vaccination':
                # Animales sin vacunación reciente (más de 6 meses)
                six_months_ago = current_date - timedelta(days=180)
                
                animals_need_vaccination = db.session.query(
                    Animals.id,
                    Animals.record,
                    func.max(Vaccinations.vaccination_date).label('last_vaccination')
                ).outerjoin(Vaccinations).filter(
                    Animals.status == AnimalStatus.Vivo
                ).group_by(
                    Animals.id, Animals.record
                ).having(
                    func.coalesce(func.max(Vaccinations.vaccination_date), '1900-01-01') < six_months_ago
                ).all()
                
                for animal in animals_need_vaccination:
                    days_without_vaccination = (current_date - (animal.last_vaccination or datetime(1900, 1, 1).date())).days
                    
                    alerts.append({
                        'id': f'vaccination_{animal.id}',
                        'type': 'vaccination',
                        'priority': 'medium',
                        'title': f'Vacunación pendiente - {animal.record}',
                        'message': f'Sin vacunación hace {days_without_vaccination} días',
                        'animal_id': animal.id,
                        'animal_record': animal.record,
                        'action_required': 'Programar vacunación',
                        'created_at': current_date.isoformat(),
                        'icon': '💉',
                        'color': 'yellow'
                    })
            
            # 4. Alertas de crecimiento - Animales con crecimiento anómalo
            if not type_filter or type_filter == 'growth':
                # Animales con pérdida de peso reciente
                recent_controls = db.session.query(
                    Animals.id,
                    Animals.record,
                    Control.id.label('control_id'),
                    Animals.weight,
                    Control.checkup_date,
                    func.lag(Animals.weight).over(
                        partition_by=Animals.id,
                        order_by=Control.checkup_date
                    ).label('previous_weight')
                ).join(Control).filter(
                    Animals.status == AnimalStatus.Vivo,
                    Control.checkup_date >= current_date - timedelta(days=90)
                ).subquery()
                
                weight_loss_animals = db.session.query(
                    recent_controls.c.id,
                    recent_controls.c.record,
                    recent_controls.c.weight,
                    recent_controls.c.previous_weight,
                    recent_controls.c.checkup_date
                ).filter(
                    recent_controls.c.previous_weight.isnot(None),
                    recent_controls.c.weight < recent_controls.c.previous_weight * 0.95  # Pérdida > 5%
                ).all()
                
                for animal in weight_loss_animals:
                    weight_loss = animal.previous_weight - animal.weight
                    loss_percentage = (weight_loss / animal.previous_weight) * 100
                    
                    alerts.append({
                        'id': f'weight_loss_{animal.id}',
                        'type': 'growth',
                        'priority': 'high',
                        'title': f'Pérdida de peso - {animal.record}',
                        'message': f'Perdió {weight_loss:.1f}kg ({loss_percentage:.1f}%)',
                        'animal_id': animal.id,
                        'animal_record': animal.record,
                        'action_required': 'Revisar alimentación y salud',
                        'created_at': animal.checkup_date.isoformat() if getattr(animal, 'checkup_date', None) else current_date.isoformat(),
                        'icon': '📉',
                        'color': 'red'
                    })
            
            # 5. Alertas de productividad - Rendimiento bajo del hato
            if not type_filter or type_filter == 'productivity':
                # Calcular promedio de ganancia diaria del último mes
                last_month = current_date - timedelta(days=30)
                
                # Cálculo de ganancia diaria promedio (versión compatible con MySQL)
                # Usamos una subquery para evitar problemas con funciones de ventana
                try:
                    # Subquery para obtener controles anteriores por animal
                    prev_control = db.session.query(
                        Control.animal_id,
                        Control.checkup_date.label('prev_date'),
                        Control.weight.label('prev_weight')
                    ).subquery()
                    
                    # Join para obtener control actual y anterior
                    weight_gains = db.session.query(
                        Control.animal_id,
                        Control.weight.label('current_weight'),
                        Control.checkup_date.label('current_date'),
                        prev_control.c.prev_weight,
                        prev_control.c.prev_date
                    ).join(
                        prev_control,
                        (Control.animal_id == prev_control.c.animal_id) &
                        (Control.checkup_date > prev_control.c.prev_date)
                    ).join(
                        Animals, Animals.id == Control.animal_id
                    ).filter(
                        Animals.status == AnimalStatus.Vivo,
                        Control.checkup_date >= last_month,
                        Control.weight.isnot(None),
                        prev_control.c.prev_weight.isnot(None)
                    ).subquery()
                    
                    # Calcular ganancia diaria
                    avg_daily_gain = db.session.query(
                        func.avg(
                            (weight_gains.c.current_weight - weight_gains.c.prev_weight) /
                            func.datediff(weight_gains.c.current_date, weight_gains.c.prev_date)
                        ).label('daily_gain')
                    ).scalar()
                    
                except Exception as calc_err:
                    logger.debug(f"No se pudo calcular avg_daily_gain: {calc_err}")
                    avg_daily_gain = None
                
                if avg_daily_gain and avg_daily_gain < 0.5:  # Menos de 500g diarios
                    alerts.append({
                        'id': 'low_productivity',
                        'type': 'productivity',
                        'priority': 'medium',
                        'title': 'Productividad baja del hato',
                        'message': f'Ganancia diaria promedio: {avg_daily_gain:.3f}kg',
                        'action_required': 'Revisar programa nutricional',
                        'created_at': current_date.isoformat(),
                        'icon': '📊',
                        'color': 'orange'
                    })
            
            # Filtrar por prioridad si se especifica
            if priority_filter:
                alerts = [alert for alert in alerts if alert['priority'] == priority_filter]
            
            # Ordenar por prioridad y fecha
            priority_order = {'high': 0, 'medium': 1, 'low': 2}
            alerts.sort(key=lambda x: (priority_order.get(x['priority'], 3), x['created_at']), reverse=True)
            
            # Limitar resultados
            alerts = alerts[:limit]
            
            # Estadísticas de alertas
            alert_stats = {
                'total': len(alerts),
                'by_priority': {
                    'high': len([a for a in alerts if a['priority'] == 'high']),
                    'medium': len([a for a in alerts if a['priority'] == 'medium']),
                    'low': len([a for a in alerts if a['priority'] == 'low'])
                },
                'by_type': {
                    'health': len([a for a in alerts if a['type'] == 'health']),
                    'vaccination': len([a for a in alerts if a['type'] == 'vaccination']),
                    'growth': len([a for a in alerts if a['type'] == 'growth']),
                    'productivity': len([a for a in alerts if a['type'] == 'productivity'])
                }
            }
            
            return APIResponse.success(
                data={
                    'alerts': alerts,
                    'statistics': alert_stats,
                    'generated_at': current_date.isoformat(),
                    'filters_applied': {
                        'priority': priority_filter,
                        'type': type_filter,
                        'limit': limit
                    }
                },
                message=f"Se generaron {len(alerts)} alertas del sistema"
            )
            
        except Exception as e:
            logger.error("Error generando alertas del sistema")
            return APIResponse.error(
                message="Error interno del servidor",
                status_code=500,
                details={'error': str(e)}
            )

@analytics_ns.route('/reports/custom')
class CustomReports(Resource):
    @analytics_ns.doc(
        'generate_custom_report',
        description='''
        **Generador de informes personalizables**
        
        Crea informes personalizados basados en criterios específicos:
        - Informes de salud animal
        - Reportes de productividad
        - Análisis de costos
        - Informes de inventario
        - Reportes de actividades
        
        **Parámetros requeridos:**
        - `report_type`: Tipo de informe (health, productivity, inventory, activities)
        - `start_date`: Fecha de inicio (YYYY-MM-DD)
        - `end_date`: Fecha de fin (YYYY-MM-DD)
        
        **Parámetros opcionales:**
        - `animal_ids`: Lista de IDs de animales específicos
        - `breed_ids`: Lista de IDs de razas
        - `format`: Formato de salida (json, summary)
        - `group_by`: Agrupar por (breed, sex, age_group, month)
        
        **Útil para:**
        - Informes ejecutivos
        - Análisis de tendencias
        - Reportes regulatorios
        ''',
        security=['Bearer', 'Cookie'],
        params={
            'report_type': {'description': 'Tipo de informe', 'type': 'string', 'enum': ['health', 'productivity', 'inventory', 'activities'], 'required': True},
            'start_date': {'description': 'Fecha de inicio (YYYY-MM-DD)', 'type': 'string', 'required': True},
            'end_date': {'description': 'Fecha de fin (YYYY-MM-DD)', 'type': 'string', 'required': True},
            'animal_ids': {'description': 'IDs de animales (separados por coma)', 'type': 'string'},
            'breed_ids': {'description': 'IDs de razas (separados por coma)', 'type': 'string'},
            'format': {'description': 'Formato de salida', 'type': 'string', 'enum': ['json', 'summary'], 'default': 'json'},
            'group_by': {'description': 'Agrupar por', 'type': 'string', 'enum': ['breed', 'sex', 'age_group', 'month']}
        },
        responses={
            200: 'Informe personalizado generado',
            400: 'Parámetros inválidos',
            401: 'Token JWT requerido o inválido',
            500: 'Error interno del servidor'
        }
    )
    @jwt_required()
    def post(self):
        """Generar informe personalizado"""
        try:
            data = request.get_json() or {}
            
            # Obtener parámetros de la petición
            report_type = data.get('report_type') or request.args.get('report_type')
            start_date_str = data.get('start_date') or request.args.get('start_date')
            end_date_str = data.get('end_date') or request.args.get('end_date')
            
            if not all([report_type, start_date_str, end_date_str]):
                return APIResponse.error(
                    message='Parámetros requeridos faltantes',
                    status_code=400,
                    details={'required_fields': 'report_type, start_date y end_date son requeridos'}
                )
            
            # Validar fechas
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return APIResponse.error(
                    message='Formato de fecha inválido. Use YYYY-MM-DD',
                    status_code=400,
                    details={'date_format': 'Formato de fecha inválido'}
                )
            
            if start_date > end_date:
                return APIResponse.error(
                    message='Rango de fechas inválido',
                    status_code=400,
                    details={'date_range': 'La fecha de inicio debe ser anterior a la fecha de fin'}
                )
            
            # Parámetros opcionales
            animal_ids = data.get('animal_ids') or request.args.get('animal_ids')
            breed_ids = data.get('breed_ids') or request.args.get('breed_ids')
            format_type = data.get('format') or request.args.get('format', 'json')
            group_by = data.get('group_by') or request.args.get('group_by')
            
            # Convertir IDs a listas
            if animal_ids:
                animal_ids = [int(id.strip()) for id in animal_ids.split(',') if id.strip().isdigit()]
            if breed_ids:
                breed_ids = [int(id.strip()) for id in breed_ids.split(',') if id.strip().isdigit()]
            
            # Generar informe según el tipo
            if report_type == 'health':
                report_data = self._generate_health_report(start_date, end_date, animal_ids, breed_ids, group_by)
            elif report_type == 'productivity':
                report_data = self._generate_productivity_report(start_date, end_date, animal_ids, breed_ids, group_by)
            elif report_type == 'inventory':
                report_data = self._generate_inventory_report(start_date, end_date, animal_ids, breed_ids, group_by)
            elif report_type == 'activities':
                report_data = self._generate_activities_report(start_date, end_date, animal_ids, breed_ids, group_by)
            else:
                return APIResponse.error(
                    message='Tipo de informe inválido',
                    status_code=400,
                    details={'report_type': 'Use: health, productivity, inventory, activities'}
                )
            
            # Formatear respuesta
            if format_type == 'summary':
                report_data = self._format_summary(report_data, report_type)
            
            return APIResponse.success(
                data={
                    'report': report_data,
                    'metadata': {
                        'report_type': report_type,
                        'period': {
                            'start_date': start_date.isoformat(),
                            'end_date': end_date.isoformat(),
                            'days': (end_date - start_date).days
                        },
                        'filters': {
                            'animal_ids': animal_ids,
                            'breed_ids': breed_ids,
                            'group_by': group_by
                        },
                        'generated_at': datetime.now().isoformat(),
                        'generated_by': get_jwt_identity().get('fullname', 'Usuario')
                    }
                },
                message=f"Informe {report_type} generado exitosamente"
            )
            
        except Exception as e:
            logger.error("Error generando informe personalizado")
            return APIResponse.error(
                message="Error interno del servidor",
                status_code=500,
                details={'error': str(e)}
            )
    
    def _generate_health_report(self, start_date, end_date, animal_ids, breed_ids, group_by):
        """Genera informe de salud"""
        # Implementar lógica específica del informe de salud
        return {
            'treatments_summary': 'Resumen de tratamientos',
            'vaccinations_summary': 'Resumen de vacunaciones',
            'health_status_distribution': 'Distribución de estados de salud'
        }
    
    def _generate_productivity_report(self, start_date, end_date, animal_ids, breed_ids, group_by):
        """Genera informe de productividad"""
        # Implementar lógica específica del informe de productividad
        return {
            'weight_gains': 'Ganancias de peso',
            'growth_rates': 'Tasas de crecimiento',
            'performance_metrics': 'Métricas de rendimiento'
        }
    
    def _generate_inventory_report(self, start_date, end_date, animal_ids, breed_ids, group_by):
        """Genera informe de inventario"""
        # Implementar lógica específica del informe de inventario
        return {
            'animal_count': 'Conteo de animales',
            'status_distribution': 'Distribución por estado',
            'breed_composition': 'Composición por raza'
        }
    
    def _generate_activities_report(self, start_date, end_date, animal_ids, breed_ids, group_by):
        """Genera informe de actividades"""
        # Implementar lógica específica del informe de actividades
        return {
            'treatments_log': 'Registro de tratamientos',
            'vaccinations_log': 'Registro de vacunaciones',
            'controls_log': 'Registro de controles'
        }
    
    def _format_summary(self, report_data, report_type):
        """Formatea el informe como resumen ejecutivo"""
        return {
            'executive_summary': f'Resumen ejecutivo del informe {report_type}',
            'key_metrics': 'Métricas clave',
            'recommendations': 'Recomendaciones'
        }

@analytics_ns.route('/animals/<int:animal_id>/medical-history')
class AnimalMedicalHistory(Resource):
    @analytics_ns.doc(
        'get_animal_medical_history',
        description='''
        **Historial médico completo de un animal**
        
        Proporciona el historial médico detallado de un animal específico:
        - Todos los tratamientos aplicados
        - Vacunaciones recibidas
        - Controles de peso y salud
        - Línea de tiempo médica
        - Alertas y recomendaciones
        
        **Parámetros:**
        - `animal_id`: ID del animal
        - `limit`: Número máximo de registros (default: 50)
        - `start_date`: Fecha de inicio (YYYY-MM-DD)
        - `end_date`: Fecha de fin (YYYY-MM-DD)
        
        **Útil para:**
        - Ficha médica individual
        - Seguimiento de tratamientos
        - Análisis de efectividad
        ''',
        security=['Bearer', 'Cookie'],
        params={
            'limit': {'description': 'Número máximo de registros', 'type': 'integer', 'default': 50},
            'start_date': {'description': 'Fecha de inicio (YYYY-MM-DD)', 'type': 'string'},
            'end_date': {'description': 'Fecha de fin (YYYY-MM-DD)', 'type': 'string'}
        },
        responses={
            200: 'Historial médico del animal',
            401: 'Token JWT requerido o inválido',
            404: 'Animal no encontrado',
            500: 'Error interno del servidor'
        }
    )
    @jwt_required()
    def get(self, animal_id):
        """Obtener historial médico completo de un animal"""
        try:
            # Verificar que el animal existe
            animal = db.session.get(Animals, animal_id)
            if not animal:
                return APIResponse.error("Animal no encontrado", status_code=404)
            
            limit = int(request.args.get('limit', 50))
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            # Filtros de fecha
            date_filter = True
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # Obtener tratamientos
            treatments_query = db.session.query(
                Treatments.id,
                Treatments.treatment_date.label('treatment_date'),
                Treatments.description.label('diagnosis'),
                Treatments.dosis.label('treatment_type'),  # Campo correcto
                literal(None).label('veterinarian')
            ).filter(Treatments.animal_id == animal_id)
            
            if start_date:
                treatments_query = treatments_query.filter(Treatments.treatment_date >= start_date)
            if end_date:
                treatments_query = treatments_query.filter(Treatments.treatment_date <= end_date)
            
            treatments = treatments_query.order_by(
                desc(Treatments.treatment_date)
            ).limit(limit).all()
            
            # Obtener vacunaciones
            vaccinations_query = db.session.query(
                Vaccinations.id,
                Vaccinations.vaccination_date,
                Vaccines.name,
                User.fullname.label('applied_by')
            ).join(Vaccines).join(
                User, User.id == Vaccinations.instructor_id
            ).filter(Vaccinations.animal_id == animal_id)
            
            if start_date:
                vaccinations_query = vaccinations_query.filter(Vaccinations.vaccination_date >= start_date)
            if end_date:
                vaccinations_query = vaccinations_query.filter(Vaccinations.vaccination_date <= end_date)
            
            vaccinations = vaccinations_query.order_by(
                desc(Vaccinations.vaccination_date)
            ).limit(limit).all()
            
            # Obtener controles
            controls_query = db.session.query(
                Control.id,
                Control.checkup_date,
                Control.id.label('control_id'),
                Control.weight,  # Asumiendo que Control tiene weight, sino Animals.weight
                Control.health_status
            ).outerjoin(Animals, Animals.id == Control.animal_id).filter(Control.animal_id == animal_id)
            
            if start_date:
                controls_query = controls_query.filter(Control.checkup_date >= start_date)
            if end_date:
                controls_query = controls_query.filter(Control.checkup_date <= end_date)
            
            controls = controls_query.order_by(
                desc(Control.checkup_date)
            ).limit(limit).all()
            
            # Crear línea de tiempo médica
            timeline = []
            
            # Agregar tratamientos
            for treatment in treatments:
                timeline.append({
                    'type': 'treatment',
                    'date': treatment.treatment_date.isoformat(),
                    'title': f'Tratamiento: {treatment.diagnosis}',
                    'description': f'Tipo: {treatment.treatment_type}',
                    'details': {
                        'id': treatment.id,
                        'diagnosis': treatment.diagnosis,
                        'treatment_type': treatment.treatment_type,
                        'veterinarian': treatment.veterinarian
                    },
                    'icon': '💊',
                    'color': 'red'
                })
            
            # Agregar vacunaciones
            for vaccination in vaccinations:
                timeline.append({
                    'type': 'vaccination',
                    'date': vaccination.vaccination_date.isoformat(),
                    'title': f'Vacunación: {vaccination.name}',
                    'description': f'Aplicada por: {vaccination.applied_by}',
                    'details': {
                        'id': vaccination.id,
                        'vaccine': vaccination.name,
                        'applied_by': vaccination.applied_by
                    },
                    'icon': '💉',
                    'color': 'green'
                })
            
            # Agregar controles
            for control in controls:
                weight = control.weight if hasattr(control, 'weight') and control.weight else (animal.weight if animal else None)
                timeline.append({
                    'type': 'control',
                    'date': control.checkup_date.isoformat(),
                    'title': f'Control de Salud',
                    'description': f'Peso: {weight}kg - Estado: {control.health_status.value if control.health_status else "N/D"}',
                    'details': {
                        'id': control.id,
                        'weight': weight,
                        'health_status': control.health_status.value if control.health_status else None
                    },
                    'icon': '📊',
                    'color': 'blue'
                })
            
            # Ordenar timeline por fecha
            timeline.sort(key=lambda x: x['date'], reverse=True)
            
            # Calcular estadísticas del animal
            total_treatments = len(treatments)
            total_vaccinations = len(vaccinations)
            total_controls = len(controls)
            
            # Tendencia de peso
            weight_trend = 'stable'
            if len(controls) >= 2:
                recent_weight = controls[0].weight
                older_weight = controls[-1].weight
                if recent_weight > older_weight * 1.05:
                    weight_trend = 'increasing'
                elif recent_weight < older_weight * 0.95:
                    weight_trend = 'decreasing'
            
            # Estado de salud actual
            current_health = controls[0].health_status.value if controls else 'Sin datos'
            
            medical_history = {
                'animal_info': {
                    'id': animal.id,
                    'record': animal.record,
                    'sex': animal.sex.value,
                    'birth_date': animal.birth_date.isoformat() if animal.birth_date else None,
                    'current_weight': animal.weight,
                    'status': animal.status.value
                },
                'summary': {
                    'total_treatments': total_treatments,
                    'total_vaccinations': total_vaccinations,
                    'total_controls': total_controls,
                    'current_health_status': current_health,
                    'weight_trend': weight_trend,
                    'last_control_date': controls[0].checkup_date.isoformat() if controls else None
                },
                'timeline': timeline[:limit],
                'treatments': [
                    {
                        'id': t.id,
                        'date': t.treatment_date.isoformat(),
                        'diagnosis': t.diagnosis,
                        'treatment_type': t.treatment_type,
                        'veterinarian': t.veterinarian
                    } for t in treatments
                ],
                'vaccinations': [
                    {
                        'id': v.id,
                        'date': v.vaccination_date.isoformat(),
                        'vaccine': v.name,
                        'applied_by': v.applied_by
                    } for v in vaccinations
                ],
                'controls': [
                    {
                        'id': c.id,
                        'date': c.checkup_date.isoformat(),
                        'weight': c.weight,
                        'health_status': c.health_status.value
                    } for c in controls
                ],
                'alerts': self._generate_health_alerts(animal, controls, treatments)
            }
            
            return APIResponse.success(
                data=medical_history,
                message=f"Historial médico de {animal.record} obtenido exitosamente"
            )
            
        except ValueError as e:
            return APIResponse.error(
                message='Formato de fecha inválido. Use YYYY-MM-DD',
                status_code=400,
                details={'field': 'date_format'}
            )
        except Exception as e:
            logger.error("Error obteniendo historial médico del animal")
            return APIResponse.error(
                message="Error interno del servidor",
                status_code=500,
                details={'error': str(e)}
            )
    
    def _generate_health_alerts(self, animal, controls, treatments):
        """Genera alertas de salud para el animal"""
        alerts = []
        
        # Sin control reciente
        if controls:
            last_control = controls[0].checkup_date
            days_since_control = (datetime.now().date() - last_control).days
            
            if days_since_control > 30:
                alerts.append({
                    'type': 'warning',
                    'message': f'Sin control hace {days_since_control} días',
                    'priority': 'medium',
                    'recommendation': 'Programar control de salud'
                })
            
            # Estado de salud preocupante
            if controls[0].health_status in [HealthStatus.Malo, HealthStatus.Regular]:
                alerts.append({
                    'type': 'danger',
                    'message': f'Estado de salud: {controls[0].health_status.value}',
                    'priority': 'high',
                    'recommendation': 'Evaluación veterinaria urgente'
                })
        else:
            alerts.append({
                'type': 'info',
                'message': 'Sin registros de control',
                'priority': 'low',
                'recommendation': 'Realizar primer control de salud'
            })
        
        # Tratamientos frecuentes
        if len(treatments) > 5:
            alerts.append({
                'type': 'warning',
                'message': f'{len(treatments)} tratamientos registrados',
                'priority': 'medium',
                'recommendation': 'Revisar plan sanitario preventivo'
            })
        
        return alerts

@analytics_ns.route('/production/statistics')
class ProductionStatistics(Resource):
    @analytics_ns.doc(
        'get_production_statistics',
        description='''
        **Estadísticas de producción y rendimiento**
        
        Análisis de productividad del hato ganadero:
        - Tendencias de peso y crecimiento
        - Tasas de conversión alimenticia
        - Métricas de rendimiento por grupo
        - Comparativas de productividad
        
        **Parámetros opcionales:**
        - `period`: Período de análisis (6m, 1y, 2y)
        - `group_by`: Agrupar por (breed, sex, age_group)
        
        **Útil para:**
        - Gráficos de tendencias
        - Análisis de rentabilidad
        - Optimización de alimentación
        ''',
        security=['Bearer', 'Cookie'],
        params={
            'period': {'description': 'Período de análisis', 'type': 'string', 'enum': ['6m', '1y', '2y'], 'default': '1y'},
            'group_by': {'description': 'Agrupar por', 'type': 'string', 'enum': ['breed', 'sex', 'age_group']}
        },
        responses={
            200: ('Estadísticas de producción', production_stats_model),
            401: 'Token JWT requerido o inválido',
            500: 'Error interno del servidor'
        }
    )
    @jwt_required()
    def get(self):
        """Obtener estadísticas de producción y rendimiento"""
        try:
            period = request.args.get('period', '1y')
            group_by = request.args.get('group_by')
            
            # Calcular fecha de inicio según período
            period_days = {
                '6m': 180,
                '1y': 365,
                '2y': 730
            }
            
            start_date = datetime.now() - timedelta(days=period_days.get(period, 365))
            
            # Tendencias de peso (basado en controles) con join correcto para evitar producto cartesiano
            weight_trends = (
                db.session.query(
                    extract('year', Control.checkup_date).label('year'),
                    extract('month', Control.checkup_date).label('month'),
                    func.avg(Control.weight).label('avg_weight'),
                    func.count(Control.id).label('count')
                )
                .join(Animals, Animals.id == Control.animal_id)
                .filter(
                    Control.checkup_date >= start_date,
                    Animals.status == AnimalStatus.Vivo
                )
                .group_by(
                    extract('year', Control.checkup_date),
                    extract('month', Control.checkup_date)
                )
                .order_by('year', 'month')
                .all()
            )
            
            # Crecimiento por animal (comparar primer y último control)
            growth_analysis = db.session.query(
                Animals.id,
                Animals.record,
                Animals.birth_date,
                func.min(Animals.weight).label('initial_weight'),
                func.max(Animals.weight).label('current_weight'),
                func.min(Control.checkup_date).label('first_control'),
                func.max(Control.checkup_date).label('last_control')
            ).join(Control).filter(
                Control.checkup_date >= start_date,
                Animals.status == AnimalStatus.Vivo
            ).group_by(
                Animals.id, Animals.record, Animals.birth_date
            ).having(
                func.count(Control.id) >= 2
            ).all()
            
            # Calcular tasas de crecimiento
            growth_rates = []
            for animal in growth_analysis:
                days_diff = (animal.last_control - animal.first_control).days
                if days_diff > 0:
                    weight_gain = animal.current_weight - animal.initial_weight
                    daily_gain = weight_gain / days_diff
                    
                    # Calcular edad aproximada
                    age_days = (datetime.now().date() - animal.birth_date).days if animal.birth_date else 0
                    age_months = age_days / 30.44
                    
                    growth_rates.append({
                        'animal_id': animal.id,
                        'record': animal.record,
                        'initial_weight': animal.initial_weight,
                        'current_weight': animal.current_weight,
                        'weight_gain': weight_gain,
                        'daily_gain': round(daily_gain, 3),
                        'period_days': days_diff,
                        'age_months': round(age_months, 1)
                    })
            
            # Estadísticas por grupo si se especifica
            group_stats = {}
            if group_by == 'breed':
                group_stats = db.session.query(
                    Breeds.name,
                    func.avg(Animals.weight).label('avg_weight'),
                    func.count(func.distinct(Animals.id)).label('animal_count')
                ).join(Animals).join(Control).filter(
                    Control.checkup_date >= start_date,
                    Animals.status == AnimalStatus.Vivo
                ).group_by(Breeds.name).all()

                group_stats = {
                    breed: {
                        'avg_weight': round(avg_weight, 2),
                        'animal_count': animal_count
                    }
                    for breed, avg_weight, animal_count in group_stats
                }
            
            elif group_by == 'sex':
                group_stats = db.session.query(
                    Animals.sex,
                    func.avg(Animals.weight).label('avg_weight'),
                    func.count(func.distinct(Animals.id)).label('animal_count')
                ).join(Control).filter(
                    Control.checkup_date >= start_date,
                    Animals.status == AnimalStatus.Vivo
                ).group_by(Animals.sex).all()
                
                group_stats = {
                    sex.value: {
                        'avg_weight': round(avg_weight, 2),
                        'animal_count': animal_count
                    }
                    for sex, avg_weight, animal_count in group_stats
                }
            
            # Métricas de productividad
            total_animals = len(growth_rates)
            avg_daily_gain = sum(gr['daily_gain'] for gr in growth_rates) / total_animals if total_animals > 0 else 0
            
            # Obtener mejor y peor ganancia diaria, asegurando que sean float
            best_daily_gain = max((gr['daily_gain'] for gr in growth_rates), default=0)
            worst_daily_gain = min((gr['daily_gain'] for gr in growth_rates), default=0)
            
            if isinstance(best_daily_gain, decimal.Decimal):
                best_daily_gain = float(best_daily_gain)
            if isinstance(worst_daily_gain, decimal.Decimal):
                worst_daily_gain = float(worst_daily_gain)
            
            best_performers = sorted(growth_rates, key=lambda x: x['daily_gain'], reverse=True)[:5]
            
            # Procesar weight_trends para asegurar que avg_weight sea float
            processed_weight_trends = []
            for year, month, avg_weight, count in weight_trends:
                if isinstance(avg_weight, decimal.Decimal):
                    avg_weight = float(avg_weight)
                processed_weight_trends.append({
                    'year': int(year),
                    'month': int(month),
                    'avg_weight': round(avg_weight, 2),
                    'sample_size': count,
                    'period': f"{int(year)}-{int(month):02d}"
                })
            
            production_data = {
                'weight_trends': processed_weight_trends,
                'growth_rates': growth_rates,
                'productivity_metrics': {
                    'total_animals_analyzed': total_animals,
                    'average_daily_gain_kg': round(avg_daily_gain, 3),
                    'best_daily_gain_kg': best_daily_gain,
                    'worst_daily_gain_kg': worst_daily_gain,
                    'period_analyzed': period
                },
                'best_performers': best_performers,
                'group_statistics': group_stats if group_by else {},
                'summary': {
                    'period': period,
                    'start_date': start_date.isoformat(),
                    'total_controls': sum(count for _, _, _, count in weight_trends),
                    'animals_with_growth_data': total_animals
                }
            }
            
            return APIResponse.success(
                data=production_data,
                message="Estadísticas de producción obtenidas exitosamente"
            )
            
        except Exception as e:
            logger.error("Error obteniendo estadísticas de producción")
            return APIResponse.error(
                message="Error interno del servidor",
                status_code=500,
                details={'error': str(e)}
            )
    
    def _get_health_alerts(self):
        """Obtiene alertas de salud importantes"""
        alerts = []
        
        # Animales sin control reciente (más de 30 días)
        month_ago = datetime.now() - timedelta(days=30)
        animals_without_control = db.session.query(Animals).filter(
            ~Animals.id.in_(
                db.session.query(Control.animal_id).filter(
                    Control.checkup_date >= month_ago
                )
            ),
            Animals.status == AnimalStatus.Vivo
        ).count()
        
        if animals_without_control > 0:
            alerts.append({
                'type': 'warning',
                'message': f'{animals_without_control} animales sin control en los últimos 30 días',
                'priority': 'medium'
            })
        
        # Animales con estado de salud malo o regular
        unhealthy_animals = db.session.query(Control).filter(
            Control.health_status.in_([HealthStatus.Malo, HealthStatus.Regular])
        ).join(Animals).filter(
            Animals.status == AnimalStatus.Vivo
        ).count()
        
        if unhealthy_animals > 0:
            alerts.append({
                'type': 'danger',
                'message': f'{unhealthy_animals} animales con estado de salud preocupante',
                'priority': 'high'
            })
        
        return alerts
    
    def _get_productivity_summary(self):
        """Obtiene resumen de productividad"""
        # Promedio de peso por grupo de edad
        current_year = datetime.now().year
        
        weight_avg = db.session.query(
            func.avg(Animals.weight).label('avg_weight')
        ).filter(
            Animals.status == AnimalStatus.Vivo
        ).scalar() or 0
        
        # Tasa de crecimiento (basada en controles)
        growth_rate = db.session.query(
            func.avg(Animals.weight).label('avg_control_weight')
        ).join(Control, Control.animal_id == Animals.id).filter(
            Control.checkup_date >= datetime(current_year, 1, 1)
        ).scalar() or 0
        
        return {
            'average_weight': round(weight_avg, 2),
            'average_control_weight': round(growth_rate, 2),
            'weight_trend': 'stable'  # Se puede calcular comparando períodos
        }

@analytics_ns.route('/animals/statistics')
class AnimalStatistics(Resource):
    @analytics_ns.doc(
        'get_animal_statistics',
        description='''
        **Estadísticas detalladas de animales**
        
        Proporciona análisis completo del inventario ganadero:
        - Distribución por estado (vivo, vendido, muerto)
        - Distribución por sexo y raza
        - Grupos de edad y distribución de pesos
        - Tendencias de crecimiento
        
        **Ideal para:**
        - Gráficos de torta y barras
        - Análisis de composición del hato
        - Planificación de reproducción
        ''',
        security=['Bearer', 'Cookie'],
        responses={
            200: ('Estadísticas de animales', animal_stats_model),
            401: 'Token JWT requerido o inválido',
            500: 'Error interno del servidor'
        }
    )
    @jwt_required()
    def get(self):
        """Obtener estadísticas detalladas de animales"""
        try:
            # Estadísticas por estado
            status_stats = db.session.query(
                Animals.status,
                func.count(Animals.id).label('count')
            ).group_by(Animals.status).all()
            
            # Estadísticas por sexo
            sex_stats = db.session.query(
                Animals.sex,
                func.count(Animals.id).label('count')
            ).group_by(Animals.sex).all()
            
            # Estadísticas por raza
            breed_stats = db.session.query(
                Breeds.name,
                func.count(Animals.id).label('count')
            ).join(Animals).group_by(Breeds.name).order_by(
                desc(func.count(Animals.id))
            ).limit(10).all()
            
            # Grupos de edad
            current_date = datetime.now().date()
            age_groups = {
                'Terneros (0-1 año)': 0,
                'Jóvenes (1-2 años)': 0,
                'Adultos (2-5 años)': 0,
                'Maduros (5+ años)': 0
            }
            
            animals_with_age = db.session.query(Animals.birth_date).filter(
                Animals.status == AnimalStatus.Vivo
            ).all()
            
            for animal in animals_with_age:
                if animal.birth_date:
                    age_years = (current_date - animal.birth_date).days / 365.25
                    if age_years < 1:
                        age_groups['Terneros (0-1 año)'] += 1
                    elif age_years < 2:
                        age_groups['Jóvenes (1-2 años)'] += 1
                    elif age_years < 5:
                        age_groups['Adultos (2-5 años)'] += 1
                    else:
                        age_groups['Maduros (5+ años)'] += 1
            
            # Distribución de pesos
            weight_ranges = {
                '0-200 kg': 0,
                '201-400 kg': 0,
                '401-600 kg': 0,
                '601+ kg': 0
            }
            
            animals_weights = db.session.query(Animals.weight).filter(
                Animals.status == AnimalStatus.Vivo
            ).all()
            
            for animal in animals_weights:
                weight = animal.weight
                if weight <= 200:
                    weight_ranges['0-200 kg'] += 1
                elif weight <= 400:
                    weight_ranges['201-400 kg'] += 1
                elif weight <= 600:
                    weight_ranges['401-600 kg'] += 1
                else:
                    weight_ranges['601+ kg'] += 1
            
            # Calcular el peso promedio y convertirlo a float para evitar problemas de serialización
            avg_weight = db.session.query(
                func.avg(Animals.weight)
            ).filter(Animals.status == AnimalStatus.Vivo).scalar() or 0
            
            if isinstance(avg_weight, decimal.Decimal):
                avg_weight = float(avg_weight)
            
            statistics_data = {
                'by_status': {
                    status.value: count for status, count in status_stats
                },
                'by_sex': {
                    sex.value: count for sex, count in sex_stats
                },
                'by_breed': [
                    {'breed': breed, 'count': count} 
                    for breed, count in breed_stats
                ],
                'by_age_group': age_groups,
                'weight_distribution': weight_ranges,
                'total_animals': sum(count for _, count in status_stats),
                'average_weight': avg_weight
            }
            
            return APIResponse.success(
                data=statistics_data,
                message="Estadísticas de animales obtenidas exitosamente"
            )
            
        except Exception as e:
            logger.error("Error obteniendo estadísticas de animales")
            return APIResponse.error(
                message="Error interno del servidor",
                status_code=500,
                details={'error': str(e)}
            )

@analytics_ns.route('/health/statistics')
class HealthStatistics(Resource):
    @analytics_ns.doc(
        'get_health_statistics',
        description='''
        **Estadísticas de salud animal**
        
        Análisis completo del estado sanitario del hato:
        - Tratamientos y vacunaciones por período
        - Distribución de estados de salud
        - Enfermedades más comunes
        - Uso de medicamentos y vacunas
        
        **Parámetros opcionales:**
        - `months`: Número de meses hacia atrás (default: 12)
        - `animal_id`: Filtrar por animal específico
        
        **Útil para:**
        - Gráficos de líneas temporales
        - Análisis de tendencias de salud
        - Planificación de programas sanitarios
        ''',
        security=['Bearer', 'Cookie'],
        params={
            'months': {'description': 'Meses hacia atrás para el análisis', 'type': 'integer', 'default': 12},
            'animal_id': {'description': 'ID de animal específico', 'type': 'integer'}
        },
        responses={
            200: ('Estadísticas de salud', health_stats_model),
            401: 'Token JWT requerido o inválido',
            500: 'Error interno del servidor'
        }
    )
    @jwt_required()
    def get(self):
        """Obtener estadísticas de salud animal"""
        try:
            months_back = int(request.args.get('months', 12))
            animal_id = request.args.get('animal_id')
            
            start_date = datetime.now() - timedelta(days=months_back * 30)
            
            # Filtros base
            treatment_query = db.session.query(Treatments).filter(
                Treatments.treatment_date >= start_date
            )
            vaccination_query = db.session.query(Vaccinations).filter(
                Vaccinations.vaccination_date >= start_date
            )
            
            if animal_id:
                treatment_query = treatment_query.filter(Treatments.animal_id == animal_id)
                vaccination_query = vaccination_query.filter(Vaccinations.animal_id == animal_id)
            
            # Tratamientos por mes
            treatments_by_month = db.session.query(
                extract('year', Treatments.treatment_date).label('year'),
                extract('month', Treatments.treatment_date).label('month'),
                func.count(Treatments.id).label('count')
            ).filter(
                Treatments.treatment_date >= start_date
            ).group_by(
                extract('year', Treatments.treatment_date),
                extract('month', Treatments.treatment_date)
            ).order_by('year', 'month').all()
            
            # Vacunaciones por mes
            vaccinations_by_month = db.session.query(
                extract('year', Vaccinations.vaccination_date).label('year'),
                extract('month', Vaccinations.vaccination_date).label('month'),
                func.count(Vaccinations.id).label('count')
            ).filter(
                Vaccinations.vaccination_date >= start_date
            ).group_by(
                extract('year', Vaccinations.vaccination_date),
                extract('month', Vaccinations.vaccination_date)
            ).order_by('year', 'month').all()
            
            # Estados de salud más recientes
            health_status_dist = db.session.query(
                Control.health_status,
                func.count(Control.id).label('count')
            ).filter(
                Control.checkup_date >= start_date
            ).group_by(Control.health_status).all()
            
            # Enfermedades más comunes (basado en diagnósticos)
            common_diseases = db.session.query(
                Treatments.description,
                func.count(Treatments.id).label('count')
            ).filter(
                Treatments.treatment_date >= start_date
            ).group_by(Treatments.description).order_by(
                desc(func.count(Treatments.id))
            ).limit(10).all()
            
            # Uso de medicamentos
            medication_usage = db.session.query(
                Medications.name,
                func.count(Treatments.id).label('usage_count')
            ).join(
                Treatments, Treatments.description.ilike(func.concat('%', Medications.name, '%'))
            ).filter(
                Treatments.treatment_date >= start_date
            ).group_by(Medications.name).order_by(
                desc(func.count(Treatments.id))
            ).limit(10).all()
            
            health_data = {
                'treatments_by_month': [
                    {
                        'year': int(year),
                        'month': int(month),
                        'count': count,
                        'period': f"{int(year)}-{int(month):02d}"
                    }
                    for year, month, count in treatments_by_month
                ],
                'vaccinations_by_month': [
                    {
                        'year': int(year),
                        'month': int(month),
                        'count': count,
                        'period': f"{int(year)}-{int(month):02d}"
                    }
                    for year, month, count in vaccinations_by_month
                ],
                'health_status_distribution': {
                    status.value: count for status, count in health_status_dist
                },
                'common_diseases': [
                    {'diagnosis': diagnosis, 'count': count}
                    for diagnosis, count in common_diseases
                ],
                'medication_usage': [
                    {'medication': medication, 'usage_count': count}
                    for medication, count in medication_usage
                ],
                'summary': {
                    'total_treatments': sum(count for _, _, count in treatments_by_month),
                    'total_vaccinations': sum(count for _, _, count in vaccinations_by_month),
                    'period_months': months_back
                }
            }
            
            return APIResponse.success(
                data=health_data,
                message="Estadísticas de salud obtenidas exitosamente"
            )
            
        except Exception as e:
            logger.error("Error obteniendo estadísticas de salud")
            return APIResponse.error(
                message="Error interno del servidor",
                status_code=500,
                details={'error': str(e)}
            )
