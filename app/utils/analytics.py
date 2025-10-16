"""
Módulo de Analytics para BackFinca
Contiene todas las funciones de cálculo de métricas, KPIs y análisis de datos
"""

from app import db
from app.models.animals import Animals, Sex, AnimalStatus
from app.models.control import Control, HealthStatus
from app.models.fields import Fields
from app.models.animalFields import AnimalFields
from app.models.diseases import Diseases
from app.models.animalDiseases import AnimalDiseases
from app.models.vaccinations import Vaccinations
from app.models.treatments import Treatments
from app.models.breeds import Breeds
from app.models.species import Species
from sqlalchemy import func, case, extract, and_, or_, desc
from datetime import datetime, timedelta, date
from collections import defaultdict
import statistics


class AnimalAnalytics:
    """Análisis y métricas relacionadas con animales"""

    @staticmethod
    def get_inventory_summary():
        """Resumen del inventario de animales"""
        total_animals = Animals.query.count()

        # Por estado
        by_status = db.session.query(
            Animals.status,
            func.count(Animals.id).label('count')
        ).group_by(Animals.status).all()

        # Por sexo (solo vivos)
        by_sex = db.session.query(
            Animals.sex,
            func.count(Animals.id).label('count')
        ).filter(Animals.status == AnimalStatus.Vivo).group_by(Animals.sex).all()

        # Por raza (solo vivos)
        by_breed = db.session.query(
            Breeds.name,
            func.count(Animals.id).label('count')
        ).join(Animals).filter(
            Animals.status == AnimalStatus.Vivo
        ).group_by(Breeds.name).all()

        return {
            'total': total_animals,
            'by_status': {str(status): count for status, count in by_status},
            'by_sex': {str(sex): count for sex, count in by_sex},
            'by_breed': {breed: count for breed, count in by_breed}
        }

    @staticmethod
    def get_age_pyramid():
        """Pirámide poblacional por edades y sexo"""
        animals = Animals.query.filter_by(status=AnimalStatus.Vivo).all()

        age_groups = {
            '0-6 meses': {'Macho': 0, 'Hembra': 0},
            '6-12 meses': {'Macho': 0, 'Hembra': 0},
            '1-2 años': {'Macho': 0, 'Hembra': 0},
            '2-3 años': {'Macho': 0, 'Hembra': 0},
            '3-5 años': {'Macho': 0, 'Hembra': 0},
            '5+ años': {'Macho': 0, 'Hembra': 0}
        }

        for animal in animals:
            age_months = AnimalAnalytics._calculate_age_months(animal.birth_date)
            sex = str(animal.sex)

            if age_months < 6:
                age_groups['0-6 meses'][sex] += 1
            elif age_months < 12:
                age_groups['6-12 meses'][sex] += 1
            elif age_months < 24:
                age_groups['1-2 años'][sex] += 1
            elif age_months < 36:
                age_groups['2-3 años'][sex] += 1
            elif age_months < 60:
                age_groups['3-5 años'][sex] += 1
            else:
                age_groups['5+ años'][sex] += 1

        return age_groups

    @staticmethod
    def get_birth_death_sales_trend(months=12):
        """Tendencia de nacimientos, muertes y ventas"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)

        # Nacimientos por mes
        births = db.session.query(
            extract('year', Animals.birth_date).label('year'),
            extract('month', Animals.birth_date).label('month'),
            func.count(Animals.id).label('count')
        ).filter(
            Animals.birth_date >= start_date
        ).group_by('year', 'month').all()

        # Muertes por mes (usando created_at como proxy de fecha de muerte)
        deaths = db.session.query(
            extract('year', Animals.updated_at).label('year'),
            extract('month', Animals.updated_at).label('month'),
            func.count(Animals.id).label('count')
        ).filter(
            Animals.status == AnimalStatus.Muerto,
            Animals.updated_at >= start_date
        ).group_by('year', 'month').all()

        # Ventas por mes
        sales = db.session.query(
            extract('year', Animals.updated_at).label('year'),
            extract('month', Animals.updated_at).label('month'),
            func.count(Animals.id).label('count')
        ).filter(
            Animals.status == AnimalStatus.Vendido,
            Animals.updated_at >= start_date
        ).group_by('year', 'month').all()

        # Formatear resultados
        result = []
        for i in range(months):
            month_date = end_date - timedelta(days=(months - i - 1) * 30)
            year, month = month_date.year, month_date.month

            birth_count = next((c for y, m, c in births if y == year and m == month), 0)
            death_count = next((c for y, m, c in deaths if y == year and m == month), 0)
            sale_count = next((c for y, m, c in sales if y == year and m == month), 0)

            result.append({
                'month': f"{year}-{month:02d}",
                'births': birth_count,
                'deaths': death_count,
                'sales': sale_count,
                'net': birth_count - death_count - sale_count
            })

        return result

    @staticmethod
    def get_reproductive_efficiency():
        """Eficiencia reproductiva de hembras"""
        females = Animals.query.filter_by(
            sex=Sex.Hembra,
            status=AnimalStatus.Vivo
        ).all()

        results = []
        for female in females:
            age_months = AnimalAnalytics._calculate_age_months(female.birth_date)

            # Solo considerar hembras reproductivas (>24 meses)
            if age_months < 24:
                continue

            offspring_count = Animals.query.filter_by(
                idMother=female.id,
                status=AnimalStatus.Vivo
            ).count()

            reproductive_years = (age_months - 24) / 12
            efficiency = offspring_count / reproductive_years if reproductive_years > 0 else 0

            results.append({
                'animal_id': female.id,
                'record': female.record,
                'age_months': age_months,
                'offspring_count': offspring_count,
                'efficiency': round(efficiency, 2)
            })

        # Ordenar por eficiencia
        results.sort(key=lambda x: x['efficiency'], reverse=True)

        return {
            'top_producers': results[:10],
            'average_efficiency': round(statistics.mean([r['efficiency'] for r in results]), 2) if results else 0,
            'total_reproductive_females': len(results)
        }

    @staticmethod
    def get_top_breeders(limit=10):
        """Top reproductores (padres y madres con más descendencia)"""
        # Padres
        fathers = db.session.query(
            Animals.id,
            Animals.record,
            Animals.sex,
            func.count(Animals.id).label('offspring')
        ).join(
            Animals,
            Animals.id == Animals.idFather,
            isouter=True
        ).group_by(Animals.id, Animals.record, Animals.sex).order_by(
            desc('offspring')
        ).limit(limit).all()

        # Madres
        mothers = db.session.query(
            Animals.id,
            Animals.record,
            Animals.sex,
            func.count(Animals.id).label('offspring')
        ).join(
            Animals,
            Animals.id == Animals.idMother,
            isouter=True
        ).group_by(Animals.id, Animals.record, Animals.sex).order_by(
            desc('offspring')
        ).limit(limit).all()

        return {
            'top_fathers': [
                {'id': id, 'record': record, 'offspring': offspring}
                for id, record, sex, offspring in fathers if offspring > 0
            ],
            'top_mothers': [
                {'id': id, 'record': record, 'offspring': offspring}
                for id, record, sex, offspring in mothers if offspring > 0
            ]
        }

    @staticmethod
    def get_genealogy_stats():
        """Estadísticas de genealogía"""
        total_animals = Animals.query.filter_by(status=AnimalStatus.Vivo).count()

        with_father = Animals.query.filter(
            Animals.status == AnimalStatus.Vivo,
            Animals.idFather.isnot(None)
        ).count()

        with_mother = Animals.query.filter(
            Animals.status == AnimalStatus.Vivo,
            Animals.idMother.isnot(None)
        ).count()

        with_both = Animals.query.filter(
            Animals.status == AnimalStatus.Vivo,
            Animals.idFather.isnot(None),
            Animals.idMother.isnot(None)
        ).count()

        return {
            'total_animals': total_animals,
            'with_father': with_father,
            'with_mother': with_mother,
            'with_complete_genealogy': with_both,
            'orphans': total_animals - with_both,
            'completeness_percentage': round((with_both / total_animals * 100), 2) if total_animals > 0 else 0
        }

    @staticmethod
    def _calculate_age_months(birth_date):
        """Calcula la edad en meses"""
        if isinstance(birth_date, str):
            birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
        today = date.today()
        return (today.year - birth_date.year) * 12 + today.month - birth_date.month


class HealthAnalytics:
    """Análisis y métricas de salud"""

    @staticmethod
    def get_health_summary():
        """Resumen del estado de salud del hato"""
        total_animals = Animals.query.filter_by(status=AnimalStatus.Vivo).count()

        # Último control de cada animal
        latest_controls = db.session.query(
            Control.animal_id,
            Control.health_status,
            func.max(Control.checkup_date).label('last_checkup')
        ).group_by(Control.animal_id).subquery()

        # Distribución de estados de salud
        health_distribution = db.session.query(
            latest_controls.c.health_status,
            func.count(latest_controls.c.animal_id).label('count')
        ).group_by(latest_controls.c.health_status).all()

        # Animales sin control reciente (>60 días)
        sixty_days_ago = date.today() - timedelta(days=60)
        animals_without_recent_control = Animals.query.filter(
            Animals.status == AnimalStatus.Vivo,
            ~Animals.id.in_(
                db.session.query(Control.animal_id).filter(
                    Control.checkup_date >= sixty_days_ago
                )
            )
        ).count()

        return {
            'total_animals': total_animals,
            'health_distribution': {str(status): count for status, count in health_distribution},
            'animals_without_recent_control': animals_without_recent_control,
            'health_index': HealthAnalytics._calculate_health_index(health_distribution, total_animals)
        }

    @staticmethod
    def get_disease_statistics(months=12):
        """Estadísticas de enfermedades"""
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 30)

        # Top enfermedades
        top_diseases = db.session.query(
            Diseases.name,
            func.count(AnimalDiseases.id).label('cases')
        ).join(AnimalDiseases).filter(
            AnimalDiseases.diagnosis_date >= start_date
        ).group_by(Diseases.name).order_by(desc('cases')).limit(10).all()

        # Enfermedades activas (sin fecha de recuperación)
        active_diseases = db.session.query(
            Diseases.name,
            func.count(AnimalDiseases.id).label('active_cases')
        ).join(AnimalDiseases).filter(
            AnimalDiseases.recovery_date.is_(None)
        ).group_by(Diseases.name).all()

        # Tasa de recuperación
        total_cases = AnimalDiseases.query.filter(
            AnimalDiseases.diagnosis_date >= start_date
        ).count()

        recovered_cases = AnimalDiseases.query.filter(
            AnimalDiseases.diagnosis_date >= start_date,
            AnimalDiseases.recovery_date.isnot(None)
        ).count()

        recovery_rate = (recovered_cases / total_cases * 100) if total_cases > 0 else 0

        return {
            'top_diseases': [{'disease': name, 'cases': cases} for name, cases in top_diseases],
            'active_diseases': [{'disease': name, 'active_cases': cases} for name, cases in active_diseases],
            'total_cases': total_cases,
            'recovered_cases': recovered_cases,
            'recovery_rate': round(recovery_rate, 2)
        }

    @staticmethod
    def detect_disease_outbreaks(days=7, threshold=3):
        """Detectar posibles brotes de enfermedades"""
        cutoff_date = date.today() - timedelta(days=days)

        recent_diseases = db.session.query(
            Diseases.name,
            func.count(AnimalDiseases.id).label('cases')
        ).join(AnimalDiseases).filter(
            AnimalDiseases.diagnosis_date >= cutoff_date
        ).group_by(Diseases.name).having(
            func.count(AnimalDiseases.id) >= threshold
        ).all()

        outbreaks = []
        for disease_name, cases in recent_diseases:
            # Obtener animales afectados y sus ubicaciones
            affected_animals = db.session.query(
                Animals.id,
                Animals.record,
                Fields.name.label('field_name')
            ).join(
                AnimalDiseases, Animals.id == AnimalDiseases.animal_id
            ).join(
                Diseases, AnimalDiseases.disease_id == Diseases.id
            ).join(
                AnimalFields, Animals.id == AnimalFields.animal_id
            ).join(
                Fields, AnimalFields.field_id == Fields.id
            ).filter(
                Diseases.name == disease_name,
                AnimalDiseases.diagnosis_date >= cutoff_date,
                AnimalFields.removal_date.is_(None)
            ).all()

            outbreaks.append({
                'disease': disease_name,
                'cases': cases,
                'severity': 'critical' if cases >= threshold * 2 else 'warning',
                'affected_fields': list(set([field for _, _, field in affected_animals])),
                'affected_animals': [{'id': id, 'record': record} for id, record, _ in affected_animals]
            })

        return outbreaks

    @staticmethod
    def get_vaccination_coverage():
        """Cobertura de vacunación"""
        total_animals = Animals.query.filter_by(status=AnimalStatus.Vivo).count()

        # Vacunaciones por tipo de vacuna
        from app.models.vaccines import Vaccines

        coverage = db.session.query(
            Vaccines.name,
            func.count(func.distinct(Vaccinations.animal_id)).label('animals_vaccinated')
        ).join(Vaccinations).join(
            Animals, Vaccinations.animal_id == Animals.id
        ).filter(
            Animals.status == AnimalStatus.Vivo
        ).group_by(Vaccines.name).all()

        return {
            'total_animals': total_animals,
            'coverage_by_vaccine': [
                {
                    'vaccine': name,
                    'animals_vaccinated': count,
                    'coverage_percentage': round((count / total_animals * 100), 2) if total_animals > 0 else 0
                }
                for name, count in coverage
            ]
        }

    @staticmethod
    def get_upcoming_vaccinations(days_ahead=30):
        """Vacunaciones próximas basadas en última aplicación"""
        # Nota: Esto requiere un campo de "próxima dosis" o "frecuencia"
        # Por ahora, retornamos animales sin vacunación reciente
        cutoff_date = date.today() - timedelta(days=180)  # 6 meses

        animals_needing_vaccination = Animals.query.filter(
            Animals.status == AnimalStatus.Vivo,
            ~Animals.id.in_(
                db.session.query(Vaccinations.animal_id).filter(
                    Vaccinations.vaccination_date >= cutoff_date
                )
            )
        ).all()

        return {
            'animals_needing_vaccination': [
                {
                    'id': animal.id,
                    'record': animal.record,
                    'last_vaccination': None
                }
                for animal in animals_needing_vaccination
            ],
            'count': len(animals_needing_vaccination)
        }

    @staticmethod
    def get_treatment_statistics():
        """Estadísticas de tratamientos"""
        # Tratamientos activos (últimos 30 días)
        thirty_days_ago = date.today() - timedelta(days=30)

        active_treatments = Treatments.query.filter(
            Treatments.treatment_date >= thirty_days_ago
        ).count()

        animals_in_treatment = db.session.query(
            func.count(func.distinct(Treatments.animal_id))
        ).filter(
            Treatments.treatment_date >= thirty_days_ago
        ).scalar()

        # Medicamentos más usados
        from app.models.medications import Medications
        from app.models.treatment_medications import TreatmentMedications

        top_medications = db.session.query(
            Medications.name,
            func.count(TreatmentMedications.id).label('uses')
        ).join(TreatmentMedications).group_by(
            Medications.name
        ).order_by(desc('uses')).limit(10).all()

        return {
            'active_treatments': active_treatments,
            'animals_in_treatment': animals_in_treatment,
            'top_medications': [
                {'medication': name, 'uses': uses}
                for name, uses in top_medications
            ]
        }

    @staticmethod
    def _calculate_health_index(health_distribution, total_animals):
        """Calcula un índice de salud (0-100)"""
        if total_animals == 0:
            return 0

        weights = {
            'Excelente': 1.0,
            'Bueno': 0.8,
            'Sano': 0.8,
            'Regular': 0.5,
            'Malo': 0.2
        }

        total_score = 0
        for status, count in health_distribution:
            status_str = str(status)
            weight = weights.get(status_str, 0.5)
            total_score += count * weight

        return round((total_score / total_animals) * 100, 2)


class FieldAnalytics:
    """Análisis y métricas de campos/potreros"""

    @staticmethod
    def get_occupation_summary():
        """Resumen de ocupación de potreros"""
        fields = Fields.query.all()

        total_capacity = 0
        total_occupied = 0
        overloaded_fields = []
        underutilized_fields = []

        for field in fields:
            capacity = int(field.capacity) if field.capacity and field.capacity.isdigit() else 0
            occupied = field.animal_fields.filter_by(removal_date=None).count()

            total_capacity += capacity
            total_occupied += occupied

            if capacity > 0:
                occupation_rate = occupied / capacity

                if occupation_rate > 1.0:
                    overloaded_fields.append({
                        'id': field.id,
                        'name': field.name,
                        'capacity': capacity,
                        'occupied': occupied,
                        'occupation_rate': round(occupation_rate * 100, 2)
                    })
                elif occupation_rate < 0.5 and occupied > 0:
                    underutilized_fields.append({
                        'id': field.id,
                        'name': field.name,
                        'capacity': capacity,
                        'occupied': occupied,
                        'occupation_rate': round(occupation_rate * 100, 2)
                    })

        return {
            'total_capacity': total_capacity,
            'total_occupied': total_occupied,
            'average_occupation': round((total_occupied / total_capacity * 100), 2) if total_capacity > 0 else 0,
            'overloaded_fields': overloaded_fields,
            'underutilized_fields': underutilized_fields,
            'available_spots': total_capacity - total_occupied
        }

    @staticmethod
    def get_field_rotation_stats():
        """Estadísticas de rotación de potreros"""
        # Promedio de tiempo de permanencia
        movements = db.session.query(
            AnimalFields.field_id,
            func.avg(
                func.julianday(AnimalFields.removal_date) -
                func.julianday(AnimalFields.assignment_date)
            ).label('avg_stay_days')
        ).filter(
            AnimalFields.removal_date.isnot(None)
        ).group_by(AnimalFields.field_id).all()

        # Potreros en descanso
        thirty_days_ago = date.today() - timedelta(days=30)
        fields_in_rest = Fields.query.filter(
            ~Fields.id.in_(
                db.session.query(AnimalFields.field_id).filter(
                    AnimalFields.removal_date.is_(None)
                )
            )
        ).all()

        return {
            'average_stay_by_field': [
                {
                    'field_id': field_id,
                    'avg_days': round(avg_days, 1) if avg_days else 0
                }
                for field_id, avg_days in movements
            ],
            'fields_in_rest': [
                {'id': field.id, 'name': field.name}
                for field in fields_in_rest
            ]
        }

    @staticmethod
    def get_field_health_map():
        """Mapa de salud por potrero"""
        fields = Fields.query.all()

        field_health = []
        for field in fields:
            # Animales actuales en el potrero
            current_animals = db.session.query(Animals.id).join(
                AnimalFields, Animals.id == AnimalFields.animal_id
            ).filter(
                AnimalFields.field_id == field.id,
                AnimalFields.removal_date.is_(None)
            ).subquery()

            # Estado de salud de esos animales
            health_status = db.session.query(
                Control.health_status,
                func.count(Control.animal_id).label('count')
            ).filter(
                Control.animal_id.in_(current_animals)
            ).group_by(Control.health_status).all()

            # Enfermedades activas en el potrero
            active_diseases = db.session.query(
                func.count(AnimalDiseases.id)
            ).filter(
                AnimalDiseases.animal_id.in_(current_animals),
                AnimalDiseases.recovery_date.is_(None)
            ).scalar()

            field_health.append({
                'field_id': field.id,
                'field_name': field.name,
                'animal_count': field.animal_fields.filter_by(removal_date=None).count(),
                'health_distribution': {str(status): count for status, count in health_status},
                'active_diseases': active_diseases or 0
            })

        return field_health


class GrowthAnalytics:
    """Análisis de crecimiento y desarrollo"""

    @staticmethod
    def calculate_adg(animal_id):
        """Calcula la Ganancia Media Diaria (GMD/ADG) de un animal"""
        controls = Control.query.filter_by(
            animal_id=animal_id
        ).order_by(Control.checkup_date).all()

        if len(controls) < 2:
            return None

        first = controls[0]
        last = controls[-1]

        days = (last.checkup_date - first.checkup_date).days
        weight_gain = (last.weight or 0) - (first.weight or 0)

        if days <= 0:
            return None

        return round(weight_gain / days, 3)

    @staticmethod
    def get_growth_curves_by_breed():
        """Curvas de crecimiento por raza"""
        breeds = Breeds.query.all()

        results = []
        for breed in breeds:
            animals = Animals.query.filter_by(
                breeds_id=breed.id,
                status=AnimalStatus.Vivo
            ).all()

            growth_data = []
            for animal in animals:
                controls = Control.query.filter_by(
                    animal_id=animal.id
                ).order_by(Control.checkup_date).all()

                for control in controls:
                    age_months = GrowthAnalytics._calculate_age_at_date(
                        animal.birth_date,
                        control.checkup_date
                    )
                    growth_data.append({
                        'age_months': age_months,
                        'weight': control.weight
                    })

            # Agrupar por edad y promediar
            age_weight_map = defaultdict(list)
            for data in growth_data:
                age_weight_map[data['age_months']].append(data['weight'])

            avg_growth = [
                {
                    'age_months': age,
                    'avg_weight': round(statistics.mean(weights), 2),
                    'count': len(weights)
                }
                for age, weights in sorted(age_weight_map.items())
            ]

            results.append({
                'breed': breed.name,
                'growth_curve': avg_growth
            })

        return results

    @staticmethod
    def get_underweight_animals():
        """Detecta animales con bajo peso para su edad"""
        animals = Animals.query.filter_by(status=AnimalStatus.Vivo).all()

        underweight = []
        for animal in animals:
            latest_control = Control.query.filter_by(
                animal_id=animal.id
            ).order_by(Control.checkup_date.desc()).first()

            if not latest_control or not latest_control.weight:
                continue

            age_months = GrowthAnalytics._calculate_age_at_date(
                animal.birth_date,
                date.today()
            )

            # Peso esperado simple (esto debería ajustarse por raza)
            expected_weight = GrowthAnalytics._expected_weight_for_age(age_months)

            if latest_control.weight < expected_weight * 0.8:  # 20% bajo el esperado
                underweight.append({
                    'id': animal.id,
                    'record': animal.record,
                    'age_months': age_months,
                    'current_weight': latest_control.weight,
                    'expected_weight': expected_weight,
                    'deficit_percentage': round(
                        ((expected_weight - latest_control.weight) / expected_weight * 100),
                        2
                    )
                })

        return underweight

    @staticmethod
    def _calculate_age_at_date(birth_date, target_date):
        """Calcula edad en meses en una fecha específica"""
        if isinstance(birth_date, str):
            birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()

        return (target_date.year - birth_date.year) * 12 + target_date.month - birth_date.month

    @staticmethod
    def _expected_weight_for_age(age_months):
        """Peso esperado simple por edad (debería ajustarse por raza)"""
        # Fórmula simple: peso al nacer (40kg) + ganancia mensual (20kg/mes)
        base_weight = 40
        monthly_gain = 20
        return base_weight + (age_months * monthly_gain)


class AlertSystem:
    """Sistema de alertas inteligentes"""

    @staticmethod
    def get_all_alerts():
        """Obtiene todas las alertas del sistema"""
        alerts = []

        # 1. Vacunaciones vencidas
        alerts.extend(AlertSystem._get_vaccination_alerts())

        # 2. Controles de salud vencidos
        alerts.extend(AlertSystem._get_health_checkup_alerts())

        # 3. Potreros sobrecargados
        alerts.extend(AlertSystem._get_overloaded_field_alerts())

        # 4. Posibles brotes de enfermedades
        alerts.extend(AlertSystem._get_disease_outbreak_alerts())

        # 5. Animales con bajo peso
        alerts.extend(AlertSystem._get_underweight_alerts())

        # 6. Animales sin movimiento
        alerts.extend(AlertSystem._get_stagnant_animal_alerts())

        # 7. Tratamientos prolongados
        alerts.extend(AlertSystem._get_prolonged_treatment_alerts())

        # Ordenar por prioridad
        priority_order = {'critical': 0, 'warning': 1, 'info': 2}
        alerts.sort(key=lambda x: priority_order.get(x['severity'], 3))

        return alerts

    @staticmethod
    def _get_vaccination_alerts():
        """Alertas de vacunación vencida"""
        # Animales sin vacunación en los últimos 180 días
        cutoff_date = date.today() - timedelta(days=180)

        animals = Animals.query.filter(
            Animals.status == AnimalStatus.Vivo,
            ~Animals.id.in_(
                db.session.query(Vaccinations.animal_id).filter(
                    Vaccinations.vaccination_date >= cutoff_date
                )
            )
        ).all()

        return [
            {
                'type': 'vaccination_overdue',
                'severity': 'warning',
                'title': 'Vacunación Vencida',
                'message': f'Animal {animal.record} no tiene vacunación reciente (>6 meses)',
                'animal_id': animal.id,
                'animal_record': animal.record
            }
            for animal in animals
        ]

    @staticmethod
    def _get_health_checkup_alerts():
        """Alertas de controles de salud vencidos"""
        cutoff_date = date.today() - timedelta(days=60)

        animals = Animals.query.filter(
            Animals.status == AnimalStatus.Vivo,
            ~Animals.id.in_(
                db.session.query(Control.animal_id).filter(
                    Control.checkup_date >= cutoff_date
                )
            )
        ).all()

        return [
            {
                'type': 'health_checkup_overdue',
                'severity': 'warning',
                'title': 'Control de Salud Vencido',
                'message': f'Animal {animal.record} sin control de salud hace más de 60 días',
                'animal_id': animal.id,
                'animal_record': animal.record
            }
            for animal in animals
        ]

    @staticmethod
    def _get_overloaded_field_alerts():
        """Alertas de potreros sobrecargados"""
        fields = Fields.query.all()
        alerts = []

        for field in fields:
            capacity = int(field.capacity) if field.capacity and field.capacity.isdigit() else 0
            occupied = field.animal_fields.filter_by(removal_date=None).count()

            if capacity > 0 and occupied > capacity:
                severity = 'critical' if occupied > capacity * 1.2 else 'warning'
                alerts.append({
                    'type': 'field_overloaded',
                    'severity': severity,
                    'title': 'Potrero Sobrecargado',
                    'message': f'Potrero {field.name} tiene {occupied} animales (capacidad: {capacity})',
                    'field_id': field.id,
                    'field_name': field.name,
                    'capacity': capacity,
                    'occupied': occupied
                })

        return alerts

    @staticmethod
    def _get_disease_outbreak_alerts():
        """Alertas de posibles brotes"""
        outbreaks = HealthAnalytics.detect_disease_outbreaks()

        return [
            {
                'type': 'disease_outbreak',
                'severity': outbreak['severity'],
                'title': 'Posible Brote de Enfermedad',
                'message': f'Detectados {outbreak["cases"]} casos de {outbreak["disease"]} en los últimos 7 días',
                'disease': outbreak['disease'],
                'cases': outbreak['cases'],
                'affected_fields': outbreak['affected_fields']
            }
            for outbreak in outbreaks
        ]

    @staticmethod
    def _get_underweight_alerts():
        """Alertas de animales con bajo peso"""
        underweight = GrowthAnalytics.get_underweight_animals()

        return [
            {
                'type': 'underweight_animal',
                'severity': 'warning',
                'title': 'Animal con Bajo Peso',
                'message': f'Animal {animal["record"]} tiene {animal["deficit_percentage"]}% menos del peso esperado',
                'animal_id': animal['id'],
                'animal_record': animal['record'],
                'deficit_percentage': animal['deficit_percentage']
            }
            for animal in underweight[:10]  # Limitar a 10
        ]

    @staticmethod
    def _get_stagnant_animal_alerts():
        """Alertas de animales sin movimiento entre potreros"""
        ninety_days_ago = date.today() - timedelta(days=90)

        stagnant = db.session.query(
            Animals.id,
            Animals.record,
            Fields.name.label('field_name'),
            AnimalFields.assignment_date
        ).join(
            AnimalFields, Animals.id == AnimalFields.animal_id
        ).join(
            Fields, AnimalFields.field_id == Fields.id
        ).filter(
            Animals.status == AnimalStatus.Vivo,
            AnimalFields.removal_date.is_(None),
            AnimalFields.assignment_date < ninety_days_ago
        ).all()

        return [
            {
                'type': 'stagnant_animal',
                'severity': 'info',
                'title': 'Animal sin Rotación',
                'message': f'Animal {record} en potrero {field_name} desde hace más de 90 días',
                'animal_id': id,
                'animal_record': record,
                'field_name': field_name,
                'days_in_field': (date.today() - assignment_date).days
            }
            for id, record, field_name, assignment_date in stagnant
        ]

    @staticmethod
    def _get_prolonged_treatment_alerts():
        """Alertas de tratamientos prolongados"""
        thirty_days_ago = date.today() - timedelta(days=30)

        prolonged = db.session.query(
            Animals.id,
            Animals.record,
            func.min(Treatments.treatment_date).label('first_treatment'),
            func.count(Treatments.id).label('treatment_count')
        ).join(
            Treatments, Animals.id == Treatments.animal_id
        ).filter(
            Animals.status == AnimalStatus.Vivo,
            Treatments.treatment_date >= thirty_days_ago
        ).group_by(Animals.id, Animals.record).having(
            func.count(Treatments.id) >= 3
        ).all()

        return [
            {
                'type': 'prolonged_treatment',
                'severity': 'warning',
                'title': 'Tratamiento Prolongado',
                'message': f'Animal {record} ha recibido {count} tratamientos en 30 días',
                'animal_id': id,
                'animal_record': record,
                'treatment_count': count,
                'days_in_treatment': (date.today() - first_treatment).days
            }
            for id, record, first_treatment, count in prolonged
        ]
