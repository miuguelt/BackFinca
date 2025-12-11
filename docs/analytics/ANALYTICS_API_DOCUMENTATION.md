# 📊 BackFinca Analytics API - Documentación Completa

## Índice
1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Dashboards Principales](#dashboards-principales)
3. [Endpoints de Animales](#endpoints-de-animales)
4. [Endpoints de Salud](#endpoints-de-salud)
5. [Endpoints de Campos](#endpoints-de-campos)
6. [Endpoints de Crecimiento](#endpoints-de-crecimiento)
7. [Sistema de Alertas](#sistema-de-alertas)
8. [Gráficos Recomendados](#gráficos-recomendados)
9. [Ejemplos de Implementación](#ejemplos-de-implementación)

---

## Resumen Ejecutivo

El sistema de analytics de BackFinca proporciona endpoints optimizados para obtener métricas, KPIs y datos analíticos sobre la gestión ganadera. Todos los endpoints están bajo `/api/analytics/`.

### Características Principales:
- ✅ **Dashboards preconstruidos** para vista ejecutiva, salud y productividad
- ✅ **Sistema de alertas inteligente** con detección automática de problemas
- ✅ **Métricas en tiempo real** con cálculos optimizados
- ✅ **Datos listos para gráficos** en formatos Chart.js y D3.js
- ✅ **Análisis avanzados** de genealogía, crecimiento y eficiencia reproductiva

---

## Dashboards Principales

### 1. Dashboard Ejecutivo Completo
**Endpoint:** `GET /api/analytics/dashboard/complete`

**Descripción:** Dashboard principal con TODAS las métricas del sistema.

**Respuesta:**
```json
{
  "success": true,
  "data": {
    // Usuarios
    "usuarios_registrados": {
      "valor": 45,
      "cambio_porcentual": 12.5,
      "descripcion": "Número total de usuarios en el sistema."
    },
    "usuarios_activos": {
      "valor": 38,
      "cambio_porcentual": 8.3,
      "descripcion": "Usuarios con actividad reciente."
    },

    // Animales
    "animales_registrados": {
      "valor": 450,
      "cambio_porcentual": 5.2
    },
    "animales_activos": {
      "valor": 420,
      "cambio_porcentual": 0
    },

    // Tratamientos y Salud
    "tratamientos_activos": {
      "valor": 12,
      "cambio_porcentual": 0
    },

    // Tareas y Alertas
    "tareas_pendientes": {
      "valor": 25,
      "cambio_porcentual": -10.5
    },
    "alertas_sistema": {
      "valor": 8,
      "cambio_porcentual": 15.2,
      "desglose": {
        "animales_sin_control": 5,
        "animales_sin_vacunacion": 2,
        "estado_salud_critico": 1
      }
    },

    // Estadísticas Adicionales
    "distribucion_sexo": {
      "machos": 180,
      "hembras": 240
    },
    "distribucion_razas_top5": [
      {"raza": "Brahman", "cantidad": 150},
      {"raza": "Angus", "cantidad": 120}
    ],
    "distribucion_estado": {
      "vivos": 420,
      "vendidos": 25,
      "muertos": 5
    },
    "peso_promedio_kg": 350.5,
    "distribucion_salud": {
      "excelente": 200,
      "bueno": 180,
      "sano": 30,
      "regular": 8,
      "malo": 2
    },
    "grupos_edad": {
      "terneros": 80,
      "jovenes": 120,
      "adultos": 180,
      "maduros": 40
    }
  }
}
```

**Uso en Frontend:**
```typescript
// React/Vue/Angular
const response = await fetch('/api/analytics/dashboard/complete', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
const { data } = await response.json();

// Mostrar KPIs
<KPICard
  title="Animales Activos"
  value={data.animales_activos.valor}
  change={data.animales_activos.cambio_porcentual}
/>
```

---

### 2. Dashboard de Salud
**Endpoint:** `GET /api/analytics/health/summary`

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "total_animals": 420,
    "health_distribution": {
      "Excelente": 200,
      "Bueno": 180,
      "Sano": 30,
      "Regular": 8,
      "Malo": 2
    },
    "animals_without_recent_control": 25,
    "health_index": 87.5
  }
}
```

---

### 3. Dashboard de Productividad
**Endpoint:** `GET /api/analytics/production/statistics`

**Parámetros:**
- `period`: 6m, 1y, 2y (default: 1y)
- `group_by`: breed, sex, age_group

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "weight_trends": [
      {"year": 2025, "month": 1, "avg_weight": 340.5, "sample_size": 50},
      {"year": 2025, "month": 2, "avg_weight": 345.2, "sample_size": 52}
    ],
    "growth_rates": [
      {
        "animal_id": 1,
        "record": "A001",
        "initial_weight": 300,
        "current_weight": 350,
        "weight_gain": 50,
        "daily_gain": 0.833,
        "period_days": 60
      }
    ],
    "productivity_metrics": {
      "total_animals_analyzed": 380,
      "average_daily_gain_kg": 0.782,
      "best_daily_gain_kg": 1.250,
      "worst_daily_gain_kg": 0.200
    },
    "best_performers": [...]
  }
}
```

---

## Endpoints de Animales

### Inventario de Animales
**Endpoint:** `GET /api/analytics/animals/inventory`

```json
{
  "total": 450,
  "by_status": {
    "Vivo": 420,
    "Vendido": 25,
    "Muerto": 5
  },
  "by_sex": {
    "Macho": 180,
    "Hembra": 240
  },
  "by_breed": {
    "Brahman": 150,
    "Angus": 120
  }
}
```

### Pirámide Poblacional
**Endpoint:** `GET /api/analytics/animals/age-pyramid`

```json
{
  "0-6 meses": {"Macho": 15, "Hembra": 18},
  "6-12 meses": {"Macho": 25, "Hembra": 30},
  "1-2 años": {"Macho": 40, "Hembra": 45},
  "2-3 años": {"Macho": 35, "Hembra": 50},
  "3-5 años": {"Macho": 45, "Hembra": 67},
  "5+ años": {"Macho": 20, "Hembra": 30}
}
```

### Tendencias de Nacimientos/Muertes/Ventas
**Endpoint:** `GET /api/analytics/animals/trends?months=12`

```json
[
  {
    "month": "2025-01",
    "births": 12,
    "deaths": 1,
    "sales": 3,
    "net": 8
  },
  {
    "month": "2025-02",
    "births": 15,
    "deaths": 0,
    "sales": 5,
    "net": 10
  }
]
```

### Eficiencia Reproductiva
**Endpoint:** `GET /api/analytics/animals/reproductive-efficiency`

```json
{
  "top_producers": [
    {
      "animal_id": 45,
      "record": "H001",
      "age_months": 60,
      "offspring_count": 5,
      "efficiency": 1.67
    }
  ],
  "average_efficiency": 0.85,
  "total_reproductive_females": 150
}
```

### Top Reproductores
**Endpoint:** `GET /api/analytics/animals/top-breeders?limit=10`

```json
{
  "top_fathers": [
    {"id": 12, "record": "M001", "offspring": 45}
  ],
  "top_mothers": [
    {"id": 45, "record": "H001", "offspring": 5}
  ]
}
```

### Estadísticas de Genealogía
**Endpoint:** `GET /api/analytics/animals/genealogy-stats`

```json
{
  "total_animals": 420,
  "with_father": 380,
  "with_mother": 375,
  "with_complete_genealogy": 360,
  "orphans": 60,
  "completeness_percentage": 85.71
}
```

---

## Endpoints de Salud

### Resumen de Salud
**Endpoint:** `GET /api/analytics/health/summary`

```json
{
  "total_animals": 420,
  "health_distribution": {
    "Excelente": 200,
    "Bueno": 180
  },
  "animals_without_recent_control": 25,
  "health_index": 87.5
}
```

### Estadísticas de Enfermedades
**Endpoint:** `GET /api/analytics/health/diseases?months=12`

```json
{
  "top_diseases": [
    {"disease": "Mastitis", "cases": 15},
    {"disease": "Parasitosis", "cases": 12}
  ],
  "active_diseases": [
    {"disease": "Mastitis", "active_cases": 3}
  ],
  "total_cases": 87,
  "recovered_cases": 75,
  "recovery_rate": 86.21
}
```

### Detección de Brotes
**Endpoint:** `GET /api/analytics/health/outbreaks?days=7&threshold=3`

```json
[
  {
    "disease": "Mastitis",
    "cases": 5,
    "severity": "critical",
    "affected_fields": ["Potrero Norte", "Potrero Sur"],
    "affected_animals": [
      {"id": 12, "record": "A012"},
      {"id": 15, "record": "A015"}
    ]
  }
]
```

### Cobertura de Vacunación
**Endpoint:** `GET /api/analytics/health/vaccination-coverage`

```json
{
  "total_animals": 420,
  "coverage_by_vaccine": [
    {
      "vaccine": "Fiebre Aftosa",
      "animals_vaccinated": 400,
      "coverage_percentage": 95.24
    },
    {
      "vaccine": "Rabia",
      "animals_vaccinated": 380,
      "coverage_percentage": 90.48
    }
  ]
}
```

### Vacunaciones Pendientes
**Endpoint:** `GET /api/analytics/health/upcoming-vaccinations?days_ahead=30`

```json
{
  "animals_needing_vaccination": [
    {
      "id": 25,
      "record": "A025",
      "last_vaccination": null
    }
  ],
  "count": 20
}
```

### Estadísticas de Tratamientos
**Endpoint:** `GET /api/analytics/health/treatments`

```json
{
  "active_treatments": 12,
  "animals_in_treatment": 10,
  "top_medications": [
    {"medication": "Ivermectina", "uses": 25},
    {"medication": "Penicilina", "uses": 18}
  ]
}
```

---

## Endpoints de Campos/Potreros

### Ocupación de Potreros
**Endpoint:** `GET /api/analytics/fields/occupation`

```json
{
  "total_capacity": 500,
  "total_occupied": 390,
  "average_occupation": 78.0,
  "overloaded_fields": [
    {
      "id": 3,
      "name": "Potrero Norte",
      "capacity": 50,
      "occupied": 60,
      "occupation_rate": 120.0
    }
  ],
  "underutilized_fields": [
    {
      "id": 5,
      "name": "Potrero Este",
      "capacity": 40,
      "occupied": 10,
      "occupation_rate": 25.0
    }
  ],
  "available_spots": 110
}
```

### Rotación de Potreros
**Endpoint:** `GET /api/analytics/fields/rotation`

```json
{
  "average_stay_by_field": [
    {"field_id": 1, "avg_days": 45.5},
    {"field_id": 2, "avg_days": 60.2}
  ],
  "fields_in_rest": [
    {"id": 7, "name": "Potrero Oeste"}
  ]
}
```

### Mapa de Salud por Potrero
**Endpoint:** `GET /api/analytics/fields/health-map`

```json
[
  {
    "field_id": 1,
    "field_name": "Potrero Norte",
    "animal_count": 45,
    "health_distribution": {
      "Excelente": 30,
      "Bueno": 12,
      "Regular": 3
    },
    "active_diseases": 2
  }
]
```

---

## Endpoints de Crecimiento

### Ganancia Media Diaria (GMD/ADG)
**Endpoint:** `GET /api/analytics/growth/adg/123`

```json
{
  "animal_id": 123,
  "adg_kg_per_day": 0.850
}
```

### Curvas de Crecimiento por Raza
**Endpoint:** `GET /api/analytics/growth/curves`

```json
[
  {
    "breed": "Brahman",
    "growth_curve": [
      {"age_months": 6, "avg_weight": 120.5, "count": 45},
      {"age_months": 12, "avg_weight": 220.3, "count": 42},
      {"age_months": 18, "avg_weight": 310.8, "count": 40}
    ]
  }
]
```

### Animales con Bajo Peso
**Endpoint:** `GET /api/analytics/growth/underweight`

```json
[
  {
    "id": 78,
    "record": "A078",
    "age_months": 12,
    "current_weight": 150,
    "expected_weight": 220,
    "deficit_percentage": 31.82
  }
]
```

---

## Sistema de Alertas

### Obtener Todas las Alertas
**Endpoint:** `GET /api/analytics/alerts?priority=high&type=health&limit=50`

**Parámetros:**
- `priority`: high, medium, low
- `type`: health, vaccination, growth, productivity
- `limit`: número máximo de alertas (default: 50)

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "alerts": [
      {
        "id": "health_12",
        "type": "health",
        "priority": "high",
        "title": "Control vencido - A012",
        "message": "Animal sin control hace 65 días",
        "animal_id": 12,
        "animal_record": "A012",
        "action_required": "Programar control de salud",
        "created_at": "2025-10-15",
        "icon": "⚠️",
        "color": "red"
      },
      {
        "id": "vaccination_25",
        "type": "vaccination",
        "priority": "medium",
        "title": "Vacunación pendiente - A025",
        "message": "Sin vacunación hace 200 días",
        "animal_id": 25,
        "animal_record": "A025",
        "action_required": "Programar vacunación",
        "created_at": "2025-10-15",
        "icon": "💉",
        "color": "yellow"
      },
      {
        "id": "field_overloaded",
        "type": "field_management",
        "priority": "critical",
        "title": "Potrero Sobrecargado",
        "message": "Potrero Norte tiene 60 animales (capacidad: 50)",
        "field_id": 3,
        "field_name": "Potrero Norte",
        "action_required": "Reubicar animales",
        "created_at": "2025-10-15",
        "icon": "🚨",
        "color": "red"
      }
    ],
    "statistics": {
      "total": 25,
      "by_priority": {
        "high": 5,
        "medium": 15,
        "low": 5
      },
      "by_type": {
        "health": 10,
        "vaccination": 8,
        "growth": 4,
        "productivity": 3
      }
    },
    "generated_at": "2025-10-15",
    "filters_applied": {
      "priority": "high",
      "type": "health",
      "limit": 50
    }
  }
}
```

---

## Gráficos Recomendados

### 1. Gráfico de Dona - Distribución por Sexo
```javascript
// Usar: GET /api/analytics/charts/animal-distribution

const chartData = {
  labels: data.by_sex.labels,  // ['Macho', 'Hembra']
  datasets: [{
    data: data.by_sex.data,     // [180, 240]
    backgroundColor: ['#3B82F6', '#EC4899']
  }]
};
```

### 2. Gráfico de Líneas - Tendencias de Inventario
```javascript
// Usar: GET /api/analytics/animals/trends?months=12

const chartData = {
  labels: data.map(d => d.month),
  datasets: [
    {
      label: 'Nacimientos',
      data: data.map(d => d.births),
      borderColor: '#10B981'
    },
    {
      label: 'Muertes',
      data: data.map(d => d.deaths),
      borderColor: '#EF4444'
    },
    {
      label: 'Ventas',
      data: data.map(d => d.sales),
      borderColor: '#F59E0B'
    }
  ]
};
```

### 3. Pirámide Poblacional
```javascript
// Usar: GET /api/analytics/animals/age-pyramid

const chartData = {
  labels: Object.keys(data),  // ['0-6 meses', '6-12 meses', ...]
  datasets: [
    {
      label: 'Machos',
      data: Object.values(data).map(d => -d.Macho),  // Negativo para lado izquierdo
      backgroundColor: '#3B82F6'
    },
    {
      label: 'Hembras',
      data: Object.values(data).map(d => d.Hembra),
      backgroundColor: '#EC4899'
    }
  ]
};
```

### 4. Heatmap - Salud por Potrero
```javascript
// Usar: GET /api/analytics/charts/health-heatmap

const heatmapData = data.map(field => ({
  x: field.field,
  y: field.health_score,
  value: field.animal_count
}));
```

### 5. Gráfico de Barras - Top Enfermedades
```javascript
// Usar: GET /api/analytics/health/diseases

const chartData = {
  labels: data.top_diseases.map(d => d.disease),
  datasets: [{
    label: 'Casos',
    data: data.top_diseases.map(d => d.cases),
    backgroundColor: '#EF4444'
  }]
};
```

---

## Ejemplos de Implementación

### React Example
```typescript
import React, { useEffect, useState } from 'react';
import { Line } from 'react-chartjs-2';

const ProductivityDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProductivityData();
  }, []);

  const fetchProductivityData = async () => {
    const response = await fetch('/api/analytics/production/statistics?period=1y', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    const result = await response.json();
    setData(result.data);
    setLoading(false);
  };

  if (loading) return <div>Cargando...</div>;

  return (
    <div className="dashboard">
      <h1>Dashboard de Productividad</h1>

      {/* KPI Cards */}
      <div className="kpi-grid">
        <KPICard
          title="GMD Promedio"
          value={`${data.productivity_metrics.average_daily_gain_kg} kg/día`}
          icon="📈"
        />
        <KPICard
          title="Mejor GMD"
          value={`${data.productivity_metrics.best_daily_gain_kg} kg/día`}
          icon="🏆"
        />
      </div>

      {/* Gráfico de Tendencias */}
      <Line
        data={{
          labels: data.weight_trends.map(t => t.period),
          datasets: [{
            label: 'Peso Promedio (kg)',
            data: data.weight_trends.map(t => t.avg_weight),
            borderColor: '#3B82F6',
            tension: 0.4
          }]
        }}
      />

      {/* Tabla de Mejores Performers */}
      <BestPerformersTable animals={data.best_performers} />
    </div>
  );
};

export default ProductivityDashboard;
```

### Vue 3 Example
```vue
<template>
  <div class="analytics-dashboard">
    <h1>Dashboard Ejecutivo</h1>

    <!-- KPI Cards -->
    <div class="grid grid-cols-4 gap-4">
      <KPICard
        :title="'Animales Activos'"
        :value="dashboard.animales_activos.valor"
        :change="dashboard.animales_activos.cambio_porcentual"
        :icon="'🐄'"
      />
      <KPICard
        :title="'Alertas'"
        :value="dashboard.alertas_sistema.valor"
        :change="dashboard.alertas_sistema.cambio_porcentual"
        :icon="'🔔'"
        :severity="dashboard.alertas_sistema.valor > 10 ? 'warning' : 'success'"
      />
    </div>

    <!-- Alertas Críticas -->
    <AlertList :alerts="criticalAlerts" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';

const dashboard = ref({});
const criticalAlerts = ref([]);

onMounted(async () => {
  // Fetch dashboard data
  const { data } = await axios.get('/api/analytics/dashboard/complete');
  dashboard.value = data.data;

  // Fetch critical alerts
  const alerts = await axios.get('/api/analytics/alerts?priority=critical');
  criticalAlerts.value = alerts.data.data.alerts;
});
</script>
```

### Angular Example
```typescript
import { Component, OnInit } from '@angular/core';
import { AnalyticsService } from './services/analytics.service';

@Component({
  selector: 'app-health-dashboard',
  templateUrl: './health-dashboard.component.html'
})
export class HealthDashboardComponent implements OnInit {
  healthData: any;
  diseases: any[];
  vaccinationCoverage: any[];

  constructor(private analyticsService: AnalyticsService) {}

  ngOnInit() {
    this.loadHealthData();
  }

  async loadHealthData() {
    this.healthData = await this.analyticsService.getHealthSummary();
    this.diseases = await this.analyticsService.getDiseaseStatistics(12);
    this.vaccinationCoverage = await this.analyticsService.getVaccinationCoverage();
  }

  getHealthIndexColor(index: number): string {
    if (index >= 90) return 'green';
    if (index >= 70) return 'yellow';
    return 'red';
  }
}
```

---

## Mejores Prácticas

### 1. Caché en el Frontend
```javascript
// Implementar caché para reducir llamadas
const cache = new Map();
const CACHE_TTL = 2 * 60 * 1000; // 2 minutos

async function fetchWithCache(url) {
  const cached = cache.get(url);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data;
  }

  const data = await fetch(url).then(r => r.json());
  cache.set(url, { data, timestamp: Date.now() });
  return data;
}
```

### 2. Manejo de Errores
```javascript
async function fetchAnalytics(endpoint) {
  try {
    const response = await fetch(`/api/analytics/${endpoint}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching analytics:', error);
    // Mostrar mensaje al usuario
    showNotification('Error al cargar datos', 'error');
    return null;
  }
}
```

### 3. Actualización Periódica
```javascript
// Actualizar dashboard cada 5 minutos
useEffect(() => {
  const interval = setInterval(() => {
    refreshDashboard();
  }, 5 * 60 * 1000);

  return () => clearInterval(interval);
}, []);
```

---

## Notas de Rendimiento

- ✅ Dashboard completo tiene **caché de 2 minutos** en el backend
- ✅ Todas las consultas usan **agregaciones SQL** en lugar de cargar datos completos
- ✅ Los endpoints de gráficos retornan datos **pre-formateados** para Chart.js
- ✅ Las alertas se calculan **bajo demanda** con filtros optimizados
- ✅ Use **paginación** en endpoints que retornan muchos registros

---

## Soporte y Contacto

Para dudas o problemas con la API de analytics:
1. Revisar esta documentación
2. Verificar los logs del servidor
3. Contactar al equipo de desarrollo

**Versión:** 2.1
**Última actualización:** 2025-10-15
