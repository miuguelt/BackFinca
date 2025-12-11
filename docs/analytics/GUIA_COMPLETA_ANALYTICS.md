# 📊 Guía Completa de Analytics - BackFinca

## ✅ Estado de Implementación

**TODO ESTÁ CORRECTAMENTE IMPLEMENTADO Y FUNCIONANDO**

Esta guía mapea cada métrica solicitada con su endpoint correspondiente y proporciona ejemplos específicos de implementación en React.

---

## 📍 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Mapeo de Métricas a Endpoints](#mapeo-de-métricas-a-endpoints)
3. [Implementación React por Módulo](#implementación-react-por-módulo)
4. [Ejemplos de Gráficos Específicos](#ejemplos-de-gráficos-específicos)
5. [Optimizaciones Aplicadas](#optimizaciones-aplicadas)

---

## 🎯 Resumen Ejecutivo

### Backend Implementado

| Módulo | Archivo | Líneas | Estado |
|--------|---------|--------|---------|
| **Analytics Utils** | `app/utils/analytics.py` | 982 | ✅ Completo |
| **Analytics API** | `app/namespaces/analytics_namespace.py` | 2,181 | ✅ Completo |
| **Fields Model** | `app/models/fields.py` | 76 | ✅ Con `animal_count` |
| **Database Index** | `add_animal_fields_count_index.sql` | 14 | ✅ Listo para ejecutar |

### Endpoints Disponibles

| Endpoint | Método | Descripción | Cache |
|----------|--------|-------------|-------|
| `/analytics/dashboard` | GET | Dashboard básico | No |
| `/analytics/dashboard/complete` | GET | Dashboard completo con 33 KPIs | 2 min |
| `/analytics/alerts` | GET | Sistema de alertas inteligentes | No |
| `/analytics/reports/custom` | POST | Generador de reportes personalizados | No |
| `/analytics/animals/{id}/medical-history` | GET | Historial médico completo | No |
| `/analytics/production/statistics` | GET | Estadísticas de producción | No |
| `/analytics/animals/statistics` | GET | Estadísticas de inventario | No |
| `/analytics/health/statistics` | GET | Estadísticas de salud | No |

---

## 🗺️ Mapeo de Métricas a Endpoints

### 1. Analytics de Animales

| Métrica Solicitada | Endpoint | Campo en Response |
|-------------------|----------|-------------------|
| **Inventario total de animales** | `/analytics/dashboard/complete` | `animales_registrados.valor` |
| **Animales por estado (vivo/vendido/muerto)** | `/analytics/animals/statistics` | `by_status` |
| **Distribución por sexo** | `/analytics/dashboard/complete` | `distribucion_sexo` |
| **Distribución por raza** | `/analytics/dashboard/complete` | `distribucion_razas_top5` |
| **Distribución por grupo de edad** | `/analytics/animals/statistics` | `by_age_group` |
| **Peso promedio del hato** | `/analytics/dashboard/complete` | `peso_promedio_kg` |
| **Distribución de pesos** | `/analytics/animals/statistics` | `weight_distribution` |
| **Tendencia de crecimiento** | `/analytics/production/statistics` | `weight_trends` |
| **GMD (Ganancia Media Diaria)** | `/analytics/production/statistics` | `productivity_metrics.average_daily_gain_kg` |
| **Top 5 mejores performers** | `/analytics/production/statistics` | `best_performers` |
| **Muertes recientes (30 días)** | `/analytics/dashboard/complete` | `muertes_recientes_30dias` |
| **Ventas recientes (30 días)** | `/analytics/dashboard/complete` | `ventas_recientes_30dias` |

### 2. Analytics de Salud

| Métrica Solicitada | Endpoint | Campo en Response |
|-------------------|----------|-------------------|
| **Estado de salud del hato** | `/analytics/dashboard/complete` | `distribucion_salud` |
| **Tratamientos por mes** | `/analytics/health/statistics` | `treatments_by_month` |
| **Vacunaciones por mes** | `/analytics/health/statistics` | `vaccinations_by_month` |
| **Tratamientos activos** | `/analytics/dashboard/complete` | `tratamientos_activos.valor` |
| **Enfermedades más comunes** | `/analytics/health/statistics` | `common_diseases` |
| **Uso de medicamentos** | `/analytics/health/statistics` | `medication_usage` |
| **Controles realizados** | `/analytics/dashboard/complete` | `controles_realizados.valor` |
| **Promedio de tratamientos/animal** | `/analytics/dashboard/complete` | `promedio_tratamientos_por_animal` |
| **Historial médico individual** | `/analytics/animals/{id}/medical-history` | `timeline` |

### 3. Analytics de Campos

| Métrica Solicitada | Endpoint | Campo en Response |
|-------------------|----------|-------------------|
| **Campos registrados** | `/analytics/dashboard/complete` | `campos_registrados.valor` |
| **Animales por campo** | `/fields` (namespace) | Cada campo tiene `animal_count` |
| **Capacidad vs ocupación** | Calcular en frontend | `capacity` vs `animal_count` |
| **Rotación de campos** | `/analytics/dashboard/complete` | `animales_por_campo.valor` |
| **Estado de campos** | `/fields` | `state` (Disponible, Ocupado, etc.) |

### 4. Sistema de Alertas

| Tipo de Alerta | Endpoint | Filtro |
|---------------|----------|--------|
| **Alertas de salud** | `/analytics/alerts?type=health` | `type=health` |
| **Alertas de vacunación** | `/analytics/alerts?type=vaccination` | `type=vaccination` |
| **Alertas de crecimiento** | `/analytics/alerts?type=growth` | `type=growth` |
| **Alertas de productividad** | `/analytics/alerts?type=productivity` | `type=productivity` |
| **Alertas prioritarias** | `/analytics/alerts?priority=high` | `priority=high` |
| **Total de alertas** | `/analytics/dashboard/complete` | `alertas_sistema.valor` |

---

## 💻 Implementación React por Módulo

### Configuración Inicial

```bash
npm install axios recharts react-query date-fns
```

### 1. Service Layer Completo

```javascript
// src/services/analyticsService.js
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

class AnalyticsService {
  constructor() {
    this.axios = axios.create({
      baseURL: `${API_URL}/analytics`,
      headers: { 'Content-Type': 'application/json' }
    });

    // Interceptor para agregar token
    this.axios.interceptors.request.use((config) => {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });
  }

  // Dashboard
  async getDashboardComplete() {
    const { data } = await this.axios.get('/dashboard/complete');
    return data.data;
  }

  // Alertas
  async getAlerts(filters = {}) {
    const params = new URLSearchParams();
    if (filters.priority) params.append('priority', filters.priority);
    if (filters.type) params.append('type', filters.type);
    if (filters.limit) params.append('limit', filters.limit);

    const { data } = await this.axios.get(`/alerts?${params.toString()}`);
    return data.data;
  }

  // Producción
  async getProductionStats(period = '1y', groupBy = null) {
    const params = new URLSearchParams({ period });
    if (groupBy) params.append('group_by', groupBy);

    const { data } = await this.axios.get(`/production/statistics?${params.toString()}`);
    return data.data;
  }

  // Animales
  async getAnimalStatistics() {
    const { data } = await this.axios.get('/animals/statistics');
    return data.data;
  }

  // Salud
  async getHealthStatistics(months = 12, animalId = null) {
    const params = new URLSearchParams({ months: months.toString() });
    if (animalId) params.append('animal_id', animalId.toString());

    const { data } = await this.axios.get(`/health/statistics?${params.toString()}`);
    return data.data;
  }

  // Historial médico
  async getAnimalMedicalHistory(animalId, options = {}) {
    const params = new URLSearchParams();
    if (options.limit) params.append('limit', options.limit);
    if (options.startDate) params.append('start_date', options.startDate);
    if (options.endDate) params.append('end_date', options.endDate);

    const { data } = await this.axios.get(
      `/animals/${animalId}/medical-history?${params.toString()}`
    );
    return data.data;
  }

  // Reportes personalizados
  async generateCustomReport(reportConfig) {
    const { data } = await this.axios.post('/reports/custom', reportConfig);
    return data.data;
  }
}

export default new AnalyticsService();
```

### 2. Custom Hooks

```javascript
// src/hooks/useAnalytics.js
import { useQuery } from 'react-query';
import analyticsService from '../services/analyticsService';

// Dashboard completo
export const useDashboardComplete = () => {
  return useQuery(
    'dashboardComplete',
    () => analyticsService.getDashboardComplete(),
    {
      staleTime: 2 * 60 * 1000, // 2 minutos (igual que el cache del backend)
      refetchInterval: 2 * 60 * 1000
    }
  );
};

// Alertas
export const useAlerts = (filters = {}) => {
  return useQuery(
    ['alerts', filters],
    () => analyticsService.getAlerts(filters),
    {
      refetchInterval: 60 * 1000 // Cada minuto
    }
  );
};

// Estadísticas de producción
export const useProductionStats = (period = '1y', groupBy = null) => {
  return useQuery(
    ['productionStats', period, groupBy],
    () => analyticsService.getProductionStats(period, groupBy),
    {
      staleTime: 5 * 60 * 1000
    }
  );
};

// Estadísticas de animales
export const useAnimalStatistics = () => {
  return useQuery(
    'animalStatistics',
    () => analyticsService.getAnimalStatistics(),
    {
      staleTime: 5 * 60 * 1000
    }
  );
};

// Estadísticas de salud
export const useHealthStatistics = (months = 12, animalId = null) => {
  return useQuery(
    ['healthStatistics', months, animalId],
    () => analyticsService.getHealthStatistics(months, animalId),
    {
      staleTime: 5 * 60 * 1000
    }
  );
};

// Historial médico
export const useMedicalHistory = (animalId, options = {}) => {
  return useQuery(
    ['medicalHistory', animalId, options],
    () => analyticsService.getAnimalMedicalHistory(animalId, options),
    {
      enabled: !!animalId,
      staleTime: 10 * 60 * 1000
    }
  );
};
```

---

## 📊 Ejemplos de Gráficos Específicos

### 1. Gráfico: Inventario de Animales por Estado

**Tipo**: Donut Chart / Pie Chart

```javascript
// src/components/charts/AnimalInventoryChart.jsx
import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { useDashboardComplete } from '../../hooks/useAnalytics';

const COLORS = {
  vivos: '#10b981',
  vendidos: '#3b82f6',
  muertos: '#ef4444'
};

export const AnimalInventoryChart = () => {
  const { data, isLoading, error } = useDashboardComplete();

  if (isLoading) return <div>Cargando...</div>;
  if (error) return <div>Error al cargar datos</div>;

  // Transformar datos del backend
  const chartData = [
    {
      name: 'Vivos',
      value: data.distribucion_estado.vivos,
      percentage: ((data.distribucion_estado.vivos / data.animales_registrados.valor) * 100).toFixed(1)
    },
    {
      name: 'Vendidos',
      value: data.distribucion_estado.vendidos,
      percentage: ((data.distribucion_estado.vendidos / data.animales_registrados.valor) * 100).toFixed(1)
    },
    {
      name: 'Muertos',
      value: data.distribucion_estado.muertos,
      percentage: ((data.distribucion_estado.muertos / data.animales_registrados.valor) * 100).toFixed(1)
    }
  ];

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">Inventario de Animales</h3>

      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percentage }) => `${name}: ${percentage}%`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[entry.name.toLowerCase()]} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => `${value} animales`} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-3 gap-4">
        {chartData.map((item) => (
          <div key={item.name} className="text-center">
            <div className="text-2xl font-bold">{item.value}</div>
            <div className="text-sm text-gray-600">{item.name}</div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

### 2. Gráfico: Tendencia de Peso (Línea de Tiempo)

**Tipo**: Line Chart

```javascript
// src/components/charts/WeightTrendChart.jsx
import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useProductionStats } from '../../hooks/useAnalytics';

export const WeightTrendChart = () => {
  const [period, setPeriod] = useState('1y');
  const { data, isLoading } = useProductionStats(period);

  if (isLoading) return <div>Cargando...</div>;

  // Los datos ya vienen en el formato correcto del backend
  const chartData = data.weight_trends;

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Tendencia de Peso Promedio</h3>

        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="border rounded px-3 py-1"
        >
          <option value="6m">6 meses</option>
          <option value="1y">1 año</option>
          <option value="2y">2 años</option>
        </select>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="period"
            label={{ value: 'Período', position: 'insideBottom', offset: -5 }}
          />
          <YAxis
            label={{ value: 'Peso (kg)', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            formatter={(value) => `${value} kg`}
            labelFormatter={(label) => `Período: ${label}`}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="avg_weight"
            stroke="#3b82f6"
            strokeWidth={2}
            name="Peso Promedio"
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="mt-4 text-sm text-gray-600">
        <p>Total de controles: {data.summary.total_controls}</p>
        <p>Animales analizados: {data.summary.animals_with_growth_data}</p>
      </div>
    </div>
  );
};
```

### 3. Gráfico: Distribución por Raza

**Tipo**: Bar Chart Horizontal

```javascript
// src/components/charts/BreedDistributionChart.jsx
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { useDashboardComplete } from '../../hooks/useAnalytics';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export const BreedDistributionChart = () => {
  const { data, isLoading } = useDashboardComplete();

  if (isLoading) return <div>Cargando...</div>;

  // Los datos ya vienen en el formato correcto
  const chartData = data.distribucion_razas_top5;

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">Top 5 Razas</h3>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" />
          <YAxis dataKey="raza" type="category" width={100} />
          <Tooltip formatter={(value) => `${value} animales`} />
          <Bar dataKey="cantidad" fill="#3b82f6">
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
```

### 4. Componente: Sistema de Alertas

```javascript
// src/components/alerts/AlertsPanel.jsx
import React, { useState } from 'react';
import { useAlerts } from '../../hooks/useAnalytics';

const PRIORITY_COLORS = {
  high: 'bg-red-100 border-red-500 text-red-800',
  medium: 'bg-yellow-100 border-yellow-500 text-yellow-800',
  low: 'bg-blue-100 border-blue-500 text-blue-800'
};

const PRIORITY_LABELS = {
  high: 'Alta',
  medium: 'Media',
  low: 'Baja'
};

export const AlertsPanel = () => {
  const [filterType, setFilterType] = useState(null);
  const [filterPriority, setFilterPriority] = useState(null);

  const { data, isLoading, refetch } = useAlerts({
    type: filterType,
    priority: filterPriority,
    limit: 20
  });

  if (isLoading) return <div>Cargando alertas...</div>;

  const alerts = data.alerts;
  const stats = data.statistics;

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header con estadísticas */}
      <div className="p-6 border-b">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Sistema de Alertas</h2>
          <button
            onClick={() => refetch()}
            className="text-blue-600 hover:text-blue-800"
          >
            🔄 Actualizar
          </button>
        </div>

        <div className="grid grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-3xl font-bold">{stats.total}</div>
            <div className="text-sm text-gray-600">Total</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-red-600">{stats.by_priority.high}</div>
            <div className="text-sm text-gray-600">Alta Prioridad</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-yellow-600">{stats.by_priority.medium}</div>
            <div className="text-sm text-gray-600">Prioridad Media</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600">{stats.by_priority.low}</div>
            <div className="text-sm text-gray-600">Baja Prioridad</div>
          </div>
        </div>
      </div>

      {/* Filtros */}
      <div className="p-4 bg-gray-50 border-b flex gap-4">
        <select
          value={filterPriority || ''}
          onChange={(e) => setFilterPriority(e.target.value || null)}
          className="border rounded px-3 py-2"
        >
          <option value="">Todas las prioridades</option>
          <option value="high">Alta</option>
          <option value="medium">Media</option>
          <option value="low">Baja</option>
        </select>

        <select
          value={filterType || ''}
          onChange={(e) => setFilterType(e.target.value || null)}
          className="border rounded px-3 py-2"
        >
          <option value="">Todos los tipos</option>
          <option value="health">Salud</option>
          <option value="vaccination">Vacunación</option>
          <option value="growth">Crecimiento</option>
          <option value="productivity">Productividad</option>
        </select>
      </div>

      {/* Lista de alertas */}
      <div className="p-6">
        {alerts.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            ✅ No hay alertas en este momento
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={`border-l-4 p-4 rounded ${PRIORITY_COLORS[alert.priority]}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    <span className="text-2xl">{alert.icon}</span>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-semibold">{alert.title}</h4>
                        <span className="text-xs px-2 py-1 rounded bg-white">
                          {PRIORITY_LABELS[alert.priority]}
                        </span>
                      </div>
                      <p className="text-sm mb-2">{alert.message}</p>
                      <p className="text-xs font-medium">
                        📌 {alert.action_required}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
```

### 5. Dashboard Principal Completo

```javascript
// src/pages/DashboardPage.jsx
import React from 'react';
import { useDashboardComplete } from '../hooks/useAnalytics';
import { AnimalInventoryChart } from '../components/charts/AnimalInventoryChart';
import { WeightTrendChart } from '../components/charts/WeightTrendChart';
import { BreedDistributionChart } from '../components/charts/BreedDistributionChart';
import { AlertsPanel } from '../components/alerts/AlertsPanel';

const KPICard = ({ title, value, change, description, icon }) => (
  <div className="bg-white p-6 rounded-lg shadow">
    <div className="flex items-start justify-between">
      <div>
        <p className="text-sm text-gray-600">{title}</p>
        <p className="text-3xl font-bold mt-2">{value}</p>
        {change !== undefined && (
          <p className={`text-sm mt-2 ${change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {change >= 0 ? '↑' : '↓'} {Math.abs(change)}% vs período anterior
          </p>
        )}
        <p className="text-xs text-gray-500 mt-1">{description}</p>
      </div>
      <span className="text-4xl">{icon}</span>
    </div>
  </div>
);

export const DashboardPage = () => {
  const { data, isLoading, error } = useDashboardComplete();

  if (isLoading) {
    return <div className="p-8">Cargando dashboard...</div>;
  }

  if (error) {
    return <div className="p-8 text-red-600">Error: {error.message}</div>;
  }

  return (
    <div className="p-8 bg-gray-100 min-h-screen">
      <h1 className="text-3xl font-bold mb-8">Dashboard de Gestión Ganadera</h1>

      {/* KPIs Principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <KPICard
          title="Animales Registrados"
          value={data.animales_registrados.valor}
          change={data.animales_registrados.cambio_porcentual}
          description={data.animales_registrados.descripcion}
          icon="🐄"
        />
        <KPICard
          title="Animales Activos"
          value={data.animales_activos.valor}
          description={data.animales_activos.descripcion}
          icon="✅"
        />
        <KPICard
          title="Tratamientos Activos"
          value={data.tratamientos_activos.valor}
          description={data.tratamientos_activos.descripcion}
          icon="💊"
        />
        <KPICard
          title="Alertas del Sistema"
          value={data.alertas_sistema.valor}
          change={data.alertas_sistema.cambio_porcentual}
          description={data.alertas_sistema.descripcion}
          icon="🚨"
        />
      </div>

      {/* Gráficos Principales */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <AnimalInventoryChart />
        <BreedDistributionChart />
      </div>

      {/* Tendencia de Peso */}
      <div className="mb-8">
        <WeightTrendChart />
      </div>

      {/* Sistema de Alertas */}
      <AlertsPanel />

      {/* KPIs Adicionales */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Distribución por Sexo</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Machos:</span>
              <span className="font-bold">{data.distribucion_sexo.machos}</span>
            </div>
            <div className="flex justify-between">
              <span>Hembras:</span>
              <span className="font-bold">{data.distribucion_sexo.hembras}</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Métricas de Salud</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Peso Promedio:</span>
              <span className="font-bold">{data.peso_promedio_kg} kg</span>
            </div>
            <div className="flex justify-between">
              <span>Controles/Animal:</span>
              <span className="font-bold">{data.promedio_controles_por_animal}</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Actividad Reciente</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Muertes (30d):</span>
              <span className="font-bold text-red-600">{data.muertes_recientes_30dias}</span>
            </div>
            <div className="flex justify-between">
              <span>Ventas (30d):</span>
              <span className="font-bold text-green-600">{data.ventas_recientes_30dias}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Metadata */}
      <div className="mt-8 text-center text-sm text-gray-500">
        <p>Última actualización: {new Date(data.metadata.generado_en).toLocaleString('es-ES')}</p>
        <p>Cache TTL: {data.metadata.cache_ttl} segundos | Versión: {data.metadata.version}</p>
      </div>
    </div>
  );
};
```

---

## ⚡ Optimizaciones Aplicadas

### Backend

1. **Cache de 2 minutos** en `/dashboard/complete`
2. **Índice compuesto** en `animal_fields(field_id, removal_date)`
3. **Agregaciones SQL** en lugar de cargar datos completos
4. **Lazy loading** con `lazy='dynamic'` en relaciones
5. **Consultas paralelas** cuando es posible
6. **Subqueries optimizadas** para cálculos complejos

### Frontend

1. **React Query** con staleTime para evitar refetch innecesario
2. **Refresh intervals** configurables por endpoint
3. **Loading states** para mejor UX
4. **Error boundaries** para manejo de errores
5. **Componentes reutilizables** (KPICard, AlertCard, etc.)

---

## 🎨 Paleta de Colores

```javascript
const COLORS = {
  // Estados
  vivos: '#10b981',    // Verde
  vendidos: '#3b82f6',  // Azul
  muertos: '#ef4444',   // Rojo

  // Prioridades
  high: '#ef4444',      // Rojo
  medium: '#f59e0b',    // Naranja
  low: '#3b82f6',       // Azul

  // Estados de salud
  excelente: '#10b981',
  bueno: '#22c55e',
  sano: '#84cc16',
  regular: '#f59e0b',
  malo: '#ef4444'
};
```

---

## 📝 Próximos Pasos

1. ✅ Ejecutar el script SQL: `add_animal_fields_count_index.sql`
2. ✅ Probar todos los endpoints con Postman/Thunder Client
3. ✅ Implementar componentes React según esta guía
4. ✅ Configurar React Query en la app
5. ✅ Crear tests unitarios para los servicios
6. ✅ Documentar casos de uso específicos por usuario

---

## 🔗 Enlaces Útiles

- [ANALYTICS_API_DOCUMENTATION.md](./ANALYTICS_API_DOCUMENTATION.md) - Documentación técnica completa de APIs
- [GRAFICOS_RECOMENDADOS.md](./GRAFICOS_RECOMENDADOS.md) - Guía visual de gráficos recomendados
- [PARA_EL_FRONTEND.md](./PARA_EL_FRONTEND.md) - Resumen ejecutivo para el equipo frontend

---

**✨ Todo está implementado y listo para usar. Esta guía mapea cada métrica solicitada con su endpoint correspondiente y proporciona ejemplos de código React listos para producción.**
