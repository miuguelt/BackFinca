# 🚀 Guía de Implementación Frontend - React

## 📋 Resumen Ejecutivo para el Equipo Frontend

Has recibido un sistema de analytics completo con **28 endpoints** listos para usar. Esta guía te ayudará a implementar todos los dashboards y gráficos en React.

---

## 🎯 Lo Esencial (TL;DR)

### Campo `animal_count` en Potreros
**Ya está listo en el backend.** Cada potrero ahora incluye `animal_count`:

```javascript
// GET /api/fields
{
  "id": 1,
  "name": "Potrero Norte",
  "capacity": "50",
  "animal_count": 45,  // ← NUEVO: Cantidad actual de animales
  "state": "Disponible"
}
```

**En tu componente React:**
```jsx
// FieldCard.jsx
const FieldCard = ({ field }) => {
  const occupancy = field.animal_count;
  const capacity = parseInt(field.capacity) || 0;
  const percentage = capacity > 0 ? Math.round((occupancy / capacity) * 100) : 0;

  return (
    <div className="field-card">
      <h3>{field.name}</h3>
      <div className="occupancy">
        <span>Ocupación del Potrero</span>
        <strong>{occupancy} / {capacity}</strong>
        <span className="percentage">{percentage}%</span>
      </div>
    </div>
  );
};
```

---

## 📦 Instalación de Dependencias

```bash
npm install axios react-query recharts chart.js react-chartjs-2
npm install @tanstack/react-query date-fns
npm install tailwindcss @headlessui/react @heroicons/react
```

**O con yarn:**
```bash
yarn add axios react-query recharts chart.js react-chartjs-2
yarn add @tanstack/react-query date-fns
yarn add tailwindcss @headlessui/react @heroicons/react
```

---

## 🏗️ Estructura de Carpetas Recomendada

```
src/
├── components/
│   ├── analytics/
│   │   ├── KPICard.jsx
│   │   ├── AlertCard.jsx
│   │   ├── ChartContainer.jsx
│   │   └── LoadingSkeleton.jsx
│   └── common/
├── pages/
│   ├── DashboardExecutive.jsx
│   ├── AnimalsAnalytics.jsx
│   ├── HealthAnalytics.jsx
│   └── FieldsAnalytics.jsx
├── services/
│   └── analyticsService.js
├── hooks/
│   └── useAnalytics.js
└── utils/
    ├── chartConfig.js
    └── colors.js
```

---

## 🔧 1. Configuración Base

### services/analyticsService.js
```javascript
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5180/api';

class AnalyticsService {
  constructor() {
    this.axios = axios.create({
      baseURL: `${API_BASE_URL}/analytics`,
      headers: {
        'Content-Type': 'application/json'
      }
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

  // Animales
  async getAnimalInventory() {
    const { data } = await this.axios.get('/animals/inventory');
    return data.data;
  }

  async getAgePyramid() {
    const { data } = await this.axios.get('/animals/age-pyramid');
    return data.data;
  }

  async getAnimalTrends(months = 12) {
    const { data } = await this.axios.get(`/animals/trends?months=${months}`);
    return data.data;
  }

  async getReproductiveEfficiency() {
    const { data } = await this.axios.get('/animals/reproductive-efficiency');
    return data.data;
  }

  // Salud
  async getHealthSummary() {
    const { data } = await this.axios.get('/health/summary');
    return data.data;
  }

  async getDiseaseStatistics(months = 12) {
    const { data } = await this.axios.get(`/health/diseases?months=${months}`);
    return data.data;
  }

  async getVaccinationCoverage() {
    const { data } = await this.axios.get('/health/vaccination-coverage');
    return data.data;
  }

  // Campos
  async getFieldOccupation() {
    const { data } = await this.axios.get('/fields/occupation');
    return data.data;
  }

  async getFieldHealthMap() {
    const { data } = await this.axios.get('/fields/health-map');
    return data.data;
  }

  // Alertas
  async getAlerts(params = {}) {
    const { data } = await this.axios.get('/alerts', { params });
    return data.data;
  }

  // Gráficos
  async getAnimalDistribution() {
    const { data } = await this.axios.get('/charts/animal-distribution');
    return data.data;
  }

  async getHealthHeatmap() {
    const { data } = await this.axios.get('/charts/health-heatmap');
    return data.data;
  }
}

export default new AnalyticsService();
```

---

## 🎨 2. Componentes Básicos

### components/analytics/KPICard.jsx
```jsx
import React from 'react';
import { ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/24/solid';

const KPICard = ({ title, value, change, icon, loading = false }) => {
  const isPositive = change >= 0;
  const changeColor = isPositive ? 'text-green-600' : 'text-red-600';
  const bgColor = isPositive ? 'bg-green-50' : 'bg-red-50';

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
        <div className="h-8 bg-gray-200 rounded w-3/4 mb-2"></div>
        <div className="h-4 bg-gray-200 rounded w-1/3"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        <span className="text-2xl">{icon}</span>
      </div>

      <div className="flex items-baseline justify-between">
        <p className="text-3xl font-bold text-gray-900">{value}</p>

        {change !== undefined && (
          <div className={`flex items-center space-x-1 ${bgColor} px-2 py-1 rounded-full`}>
            {isPositive ? (
              <ArrowUpIcon className={`w-4 h-4 ${changeColor}`} />
            ) : (
              <ArrowDownIcon className={`w-4 h-4 ${changeColor}`} />
            )}
            <span className={`text-sm font-semibold ${changeColor}`}>
              {Math.abs(change).toFixed(1)}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default KPICard;
```

### components/analytics/AlertCard.jsx
```jsx
import React from 'react';
import {
  ExclamationTriangleIcon,
  XCircleIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline';

const AlertCard = ({ alert, onAction }) => {
  const severityConfig = {
    critical: {
      icon: XCircleIcon,
      bgColor: 'bg-red-50',
      borderColor: 'border-red-500',
      textColor: 'text-red-800',
      buttonColor: 'bg-red-600 hover:bg-red-700'
    },
    warning: {
      icon: ExclamationTriangleIcon,
      bgColor: 'bg-yellow-50',
      borderColor: 'border-yellow-500',
      textColor: 'text-yellow-800',
      buttonColor: 'bg-yellow-600 hover:bg-yellow-700'
    },
    info: {
      icon: InformationCircleIcon,
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-500',
      textColor: 'text-blue-800',
      buttonColor: 'bg-blue-600 hover:bg-blue-700'
    }
  };

  const config = severityConfig[alert.severity] || severityConfig.info;
  const Icon = config.icon;

  return (
    <div className={`${config.bgColor} border-l-4 ${config.borderColor} p-4 rounded-r-lg`}>
      <div className="flex items-start">
        <Icon className={`w-5 h-5 ${config.textColor} mt-0.5`} />
        <div className="ml-3 flex-1">
          <h3 className={`text-sm font-semibold ${config.textColor}`}>
            {alert.title}
          </h3>
          <p className={`text-sm ${config.textColor} mt-1`}>
            {alert.message}
          </p>
          {alert.action_required && (
            <button
              onClick={() => onAction(alert)}
              className={`mt-3 px-4 py-2 text-xs font-medium text-white rounded-md ${config.buttonColor} transition-colors`}
            >
              {alert.action_required}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default AlertCard;
```

---

## 📊 3. Hooks Personalizados

### hooks/useAnalytics.js
```javascript
import { useQuery } from '@tanstack/react-query';
import analyticsService from '../services/analyticsService';

export const useAnalytics = () => {
  // Dashboard
  const useDashboard = () =>
    useQuery({
      queryKey: ['dashboard-complete'],
      queryFn: () => analyticsService.getDashboardComplete(),
      staleTime: 2 * 60 * 1000, // 2 minutos
      refetchInterval: 5 * 60 * 1000 // Refetch cada 5 minutos
    });

  // Animales
  const useAnimalInventory = () =>
    useQuery({
      queryKey: ['animal-inventory'],
      queryFn: () => analyticsService.getAnimalInventory(),
      staleTime: 2 * 60 * 1000
    });

  const useAnimalTrends = (months = 12) =>
    useQuery({
      queryKey: ['animal-trends', months],
      queryFn: () => analyticsService.getAnimalTrends(months),
      staleTime: 5 * 60 * 1000
    });

  // Salud
  const useHealthSummary = () =>
    useQuery({
      queryKey: ['health-summary'],
      queryFn: () => analyticsService.getHealthSummary(),
      staleTime: 2 * 60 * 1000
    });

  const useDiseases = (months = 12) =>
    useQuery({
      queryKey: ['diseases', months],
      queryFn: () => analyticsService.getDiseaseStatistics(months),
      staleTime: 5 * 60 * 1000
    });

  // Alertas
  const useAlerts = (params = {}) =>
    useQuery({
      queryKey: ['alerts', params],
      queryFn: () => analyticsService.getAlerts(params),
      staleTime: 1 * 60 * 1000, // 1 minuto (más frecuente)
      refetchInterval: 2 * 60 * 1000
    });

  // Campos
  const useFieldOccupation = () =>
    useQuery({
      queryKey: ['field-occupation'],
      queryFn: () => analyticsService.getFieldOccupation(),
      staleTime: 2 * 60 * 1000
    });

  return {
    useDashboard,
    useAnimalInventory,
    useAnimalTrends,
    useHealthSummary,
    useDiseases,
    useAlerts,
    useFieldOccupation
  };
};
```

---

## 🎯 4. Dashboard Ejecutivo Completo

### pages/DashboardExecutive.jsx
```jsx
import React from 'react';
import { useAnalytics } from '../hooks/useAnalytics';
import KPICard from '../components/analytics/KPICard';
import AlertCard from '../components/analytics/AlertCard';
import { Line, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

// Registrar componentes de Chart.js
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const DashboardExecutive = () => {
  const { useDashboard, useAnimalTrends, useAlerts } = useAnalytics();

  const { data: dashboard, isLoading: loadingDashboard } = useDashboard();
  const { data: trends, isLoading: loadingTrends } = useAnimalTrends(12);
  const { data: alerts, isLoading: loadingAlerts } = useAlerts({ priority: 'critical', limit: 5 });

  if (loadingDashboard) {
    return <LoadingDashboard />;
  }

  // Datos para gráfico de dona
  const sexDistributionData = {
    labels: ['Machos', 'Hembras'],
    datasets: [{
      data: [
        dashboard.distribucion_sexo.machos,
        dashboard.distribucion_sexo.hembras
      ],
      backgroundColor: ['#3B82F6', '#EC4899'],
      borderWidth: 2,
      borderColor: '#fff'
    }]
  };

  // Datos para gráfico de líneas
  const trendsData = trends ? {
    labels: trends.map(t => {
      const [year, month] = t.month.split('-');
      return new Date(year, month - 1).toLocaleDateString('es', { month: 'short' });
    }),
    datasets: [
      {
        label: 'Nacimientos',
        data: trends.map(t => t.births),
        borderColor: '#10B981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        tension: 0.4,
        fill: true
      },
      {
        label: 'Muertes',
        data: trends.map(t => t.deaths),
        borderColor: '#EF4444',
        tension: 0.4
      },
      {
        label: 'Ventas',
        data: trends.map(t => t.sales),
        borderColor: '#F59E0B',
        tension: 0.4
      }
    ]
  } : null;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard Ejecutivo</h1>
        <p className="text-gray-600 mt-2">Vista general del estado de la finca</p>
      </div>

      {/* KPIs Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <KPICard
          title="Animales Registrados"
          value={dashboard.animales_registrados.valor}
          change={dashboard.animales_registrados.cambio_porcentual}
          icon="🐄"
          loading={loadingDashboard}
        />
        <KPICard
          title="Animales Vivos"
          value={dashboard.animales_activos.valor}
          change={dashboard.animales_activos.cambio_porcentual}
          icon="💚"
          loading={loadingDashboard}
        />
        <KPICard
          title="Índice de Salud"
          value={`${dashboard.distribucion_salud.excelente + dashboard.distribucion_salud.bueno}/${dashboard.animales_activos.valor}`}
          icon="🏥"
          loading={loadingDashboard}
        />
        <KPICard
          title="Alertas Activas"
          value={dashboard.alertas_sistema.valor}
          change={dashboard.alertas_sistema.cambio_porcentual}
          icon="🔔"
          loading={loadingDashboard}
        />
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Gráfico de Dona */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Distribución por Sexo
          </h2>
          <div className="h-64 flex items-center justify-center">
            <Doughnut
              data={sexDistributionData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: 'bottom'
                  },
                  tooltip: {
                    callbacks: {
                      label: (context) => {
                        const total = dashboard.distribucion_sexo.machos +
                                    dashboard.distribucion_sexo.hembras;
                        const percentage = ((context.parsed / total) * 100).toFixed(1);
                        return `${context.label}: ${context.parsed} (${percentage}%)`;
                      }
                    }
                  }
                }
              }}
            />
          </div>
        </div>

        {/* Gráfico de Líneas */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Tendencia de Inventario (12 meses)
          </h2>
          <div className="h-64">
            {trendsData ? (
              <Line
                data={trendsData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  interaction: {
                    mode: 'index',
                    intersect: false
                  },
                  plugins: {
                    legend: {
                      position: 'bottom'
                    }
                  },
                  scales: {
                    y: {
                      beginAtZero: true
                    }
                  }
                }}
              />
            ) : (
              <div className="flex items-center justify-center h-full">
                <p className="text-gray-400">Cargando datos...</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Alertas Críticas */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Alertas Críticas
          </h2>
          <span className="px-3 py-1 bg-red-100 text-red-800 text-sm font-medium rounded-full">
            {alerts?.alerts?.length || 0} activas
          </span>
        </div>

        {loadingAlerts ? (
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-20 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        ) : alerts?.alerts?.length > 0 ? (
          <div className="space-y-4">
            {alerts.alerts.map(alert => (
              <AlertCard
                key={alert.id || alert.type}
                alert={alert}
                onAction={(alert) => console.log('Action:', alert)}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p className="text-4xl mb-2">✅</p>
            <p>No hay alertas críticas</p>
          </div>
        )}
      </div>

      {/* Estadísticas Adicionales */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        {/* Distribución por Raza */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Top 5 Razas
          </h3>
          <div className="space-y-3">
            {dashboard.distribucion_razas_top5.slice(0, 5).map((raza, index) => {
              const total = dashboard.animales_activos.valor;
              const percentage = ((raza.cantidad / total) * 100).toFixed(1);
              return (
                <div key={index} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">{raza.raza}</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-24 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold text-gray-900 w-12 text-right">
                      {raza.cantidad}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Estado de Salud */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Estado de Salud
          </h3>
          <div className="space-y-3">
            {Object.entries(dashboard.distribucion_salud).map(([estado, cantidad]) => (
              <div key={estado} className="flex items-center justify-between">
                <span className="text-sm text-gray-600 capitalize">{estado}</span>
                <span className="text-sm font-semibold text-gray-900">{cantidad}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Grupos de Edad */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Grupos de Edad
          </h3>
          <div className="space-y-3">
            {Object.entries(dashboard.grupos_edad).map(([grupo, cantidad]) => (
              <div key={grupo} className="flex items-center justify-between">
                <span className="text-sm text-gray-600 capitalize">{grupo}</span>
                <span className="text-sm font-semibold text-gray-900">{cantidad}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// Componente de Loading
const LoadingDashboard = () => (
  <div className="min-h-screen bg-gray-50 p-6">
    <div className="mb-8 animate-pulse">
      <div className="h-8 bg-gray-200 rounded w-1/4 mb-2"></div>
      <div className="h-4 bg-gray-200 rounded w-1/3"></div>
    </div>
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {[1, 2, 3, 4].map(i => (
        <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
          <div className="h-8 bg-gray-200 rounded w-3/4 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-1/3"></div>
        </div>
      ))}
    </div>
  </div>
);

export default DashboardExecutive;
```

---

## 🏞️ 5. Vista de Potreros con animal_count

### components/FieldCard.jsx
```jsx
import React from 'react';
import { MapPinIcon, ChartBarIcon } from '@heroicons/react/24/outline';

const FieldCard = ({ field }) => {
  const capacity = parseInt(field.capacity) || 0;
  const occupied = field.animal_count || 0;
  const occupationRate = capacity > 0 ? (occupied / capacity) * 100 : 0;

  // Determinar color según ocupación
  const getOccupationColor = () => {
    if (occupationRate > 100) return 'text-red-600 bg-red-50';
    if (occupationRate > 80) return 'text-yellow-600 bg-yellow-50';
    if (occupationRate > 50) return 'text-green-600 bg-green-50';
    return 'text-gray-600 bg-gray-50';
  };

  const getProgressColor = () => {
    if (occupationRate > 100) return 'bg-red-600';
    if (occupationRate > 80) return 'bg-yellow-500';
    if (occupationRate > 50) return 'bg-green-500';
    return 'bg-gray-400';
  };

  return (
    <div className="bg-white rounded-lg shadow hover:shadow-lg transition-all p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{field.name}</h3>
          <div className="flex items-center mt-1 text-sm text-gray-500">
            <MapPinIcon className="w-4 h-4 mr-1" />
            {field.ubication || 'Sin ubicación'}
          </div>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
          field.state === 'Disponible' ? 'bg-green-100 text-green-800' :
          field.state === 'Ocupado' ? 'bg-blue-100 text-blue-800' :
          'bg-gray-100 text-gray-800'
        }`}>
          {field.state}
        </span>
      </div>

      {/* Ocupación */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-600">
            Ocupación del Potrero
          </span>
          <span className={`text-lg font-bold ${getOccupationColor()}`}>
            {occupied} / {capacity}
          </span>
        </div>

        {/* Barra de progreso */}
        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
          <div
            className={`h-3 rounded-full transition-all duration-500 ${getProgressColor()}`}
            style={{ width: `${Math.min(occupationRate, 100)}%` }}
          />
        </div>

        <div className="flex items-center justify-between mt-1">
          <span className="text-xs text-gray-500">0%</span>
          <span className={`text-xs font-semibold ${getOccupationColor()}`}>
            {occupationRate.toFixed(0)}%
          </span>
          <span className="text-xs text-gray-500">100%</span>
        </div>
      </div>

      {/* Alertas */}
      {occupationRate > 100 && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-xs text-red-800 font-medium">
            ⚠️ Potrero sobrecargado ({(occupationRate - 100).toFixed(0)}% sobre capacidad)
          </p>
        </div>
      )}

      {/* Información adicional */}
      <div className="mt-4 pt-4 border-t border-gray-200 grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-600">Área:</span>
          <span className="ml-2 font-medium text-gray-900">{field.area}</span>
        </div>
        <div>
          <span className="text-gray-600">Tipo Alimento:</span>
          <span className="ml-2 font-medium text-gray-900">
            {field.food_types?.name || 'N/A'}
          </span>
        </div>
      </div>

      {/* Botones de acción */}
      <div className="mt-4 flex space-x-2">
        <button className="flex-1 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors">
          Ver Detalles
        </button>
        <button className="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-50 transition-colors">
          <ChartBarIcon className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};

export default FieldCard;
```

### pages/FieldsPage.jsx
```jsx
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import FieldCard from '../components/FieldCard';
import { useAnalytics } from '../hooks/useAnalytics';

const FieldsPage = () => {
  const [searchTerm, setSearchTerm] = useState('');

  // Obtener lista de potreros
  const { data: fieldsData, isLoading } = useQuery({
    queryKey: ['fields'],
    queryFn: async () => {
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:5180/api/fields', {
        headers: { Authorization: `Bearer ${token}` }
      });
      return response.data.data;
    }
  });

  // Obtener métricas de ocupación
  const { useFieldOccupation } = useAnalytics();
  const { data: occupation } = useFieldOccupation();

  const filteredFields = fieldsData?.items?.filter(field =>
    field.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    field.ubication?.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Gestión de Potreros</h1>
        <p className="text-gray-600 mt-2">Administra y monitorea tus campos</p>
      </div>

      {/* Métricas Resumen */}
      {occupation && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-sm text-gray-600">Capacidad Total</p>
            <p className="text-3xl font-bold text-gray-900">{occupation.total_capacity}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-sm text-gray-600">Animales Ubicados</p>
            <p className="text-3xl font-bold text-blue-600">{occupation.total_occupied}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-sm text-gray-600">Ocupación Promedio</p>
            <p className="text-3xl font-bold text-green-600">{occupation.average_occupation}%</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-sm text-gray-600">Espacios Disponibles</p>
            <p className="text-3xl font-bold text-gray-900">{occupation.available_spots}</p>
          </div>
        </div>
      )}

      {/* Buscador */}
      <div className="mb-6">
        <input
          type="text"
          placeholder="Buscar potreros..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full md:w-96 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* Grid de Potreros */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
              <div className="h-6 bg-gray-200 rounded w-3/4 mb-4"></div>
              <div className="h-4 bg-gray-200 rounded w-1/2 mb-6"></div>
              <div className="h-3 bg-gray-200 rounded mb-2"></div>
              <div className="h-12 bg-gray-200 rounded"></div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredFields.map(field => (
            <FieldCard key={field.id} field={field} />
          ))}
        </div>
      )}

      {filteredFields.length === 0 && !isLoading && (
        <div className="text-center py-12">
          <p className="text-gray-500 text-lg">No se encontraron potreros</p>
        </div>
      )}
    </div>
  );
};

export default FieldsPage;
```

---

## 🔔 6. Panel de Alertas

### components/AlertsPanel.jsx
```jsx
import React, { useState } from 'react';
import { useAnalytics } from '../hooks/useAnalytics';
import AlertCard from './analytics/AlertCard';
import { FunnelIcon } from '@heroicons/react/24/outline';

const AlertsPanel = () => {
  const [priority, setPriority] = useState('all');
  const { useAlerts } = useAnalytics();

  const params = priority !== 'all' ? { priority, limit: 50 } : { limit: 50 };
  const { data, isLoading, refetch } = useAlerts(params);

  const handleAction = async (alert) => {
    console.log('Handling alert:', alert);
    // Aquí puedes navegar o ejecutar acciones específicas
    switch (alert.type) {
      case 'vaccination_overdue':
        // Navegar a programar vacunación
        break;
      case 'health_checkup_overdue':
        // Navegar a programar control
        break;
      case 'field_overloaded':
        // Navegar a gestión de campos
        break;
      default:
        break;
    }
  };

  const priorities = [
    { value: 'all', label: 'Todas', color: 'gray' },
    { value: 'critical', label: 'Críticas', color: 'red' },
    { value: 'warning', label: 'Advertencias', color: 'yellow' },
    { value: 'info', label: 'Información', color: 'blue' }
  ];

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header con filtros */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">
            Sistema de Alertas
          </h2>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            Actualizar
          </button>
        </div>

        {/* Filtros */}
        <div className="flex items-center space-x-2">
          <FunnelIcon className="w-5 h-5 text-gray-400" />
          <span className="text-sm text-gray-600">Filtrar por:</span>
          {priorities.map(p => (
            <button
              key={p.value}
              onClick={() => setPriority(p.value)}
              className={`px-3 py-1 text-sm font-medium rounded-full transition-colors ${
                priority === p.value
                  ? `bg-${p.color}-100 text-${p.color}-800`
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Lista de alertas */}
      <div className="p-6">
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-24 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        ) : data?.alerts && data.alerts.length > 0 ? (
          <>
            {/* Estadísticas */}
            {data.statistics && (
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="text-center p-3 bg-red-50 rounded-lg">
                  <p className="text-2xl font-bold text-red-600">
                    {data.statistics.by_priority?.high || 0}
                  </p>
                  <p className="text-sm text-red-800">Críticas</p>
                </div>
                <div className="text-center p-3 bg-yellow-50 rounded-lg">
                  <p className="text-2xl font-bold text-yellow-600">
                    {data.statistics.by_priority?.medium || 0}
                  </p>
                  <p className="text-sm text-yellow-800">Advertencias</p>
                </div>
                <div className="text-center p-3 bg-blue-50 rounded-lg">
                  <p className="text-2xl font-bold text-blue-600">
                    {data.statistics.by_priority?.low || 0}
                  </p>
                  <p className="text-sm text-blue-800">Información</p>
                </div>
              </div>
            )}

            {/* Alertas */}
            <div className="space-y-4">
              {data.alerts.map((alert, index) => (
                <AlertCard
                  key={alert.id || index}
                  alert={alert}
                  onAction={handleAction}
                />
              ))}
            </div>
          </>
        ) : (
          <div className="text-center py-12">
            <p className="text-4xl mb-2">✅</p>
            <p className="text-gray-500">No hay alertas en este momento</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AlertsPanel;
```

---

## 🎨 7. Configuración de Colores

### utils/colors.js
```javascript
export const COLORS = {
  // Animales
  animals: {
    male: '#3B82F6',
    female: '#EC4899',
    alive: '#10B981',
    dead: '#EF4444',
    sold: '#F59E0B'
  },

  // Salud
  health: {
    excellent: '#10B981',
    good: '#3B82F6',
    healthy: '#8B5CF6',
    regular: '#F59E0B',
    bad: '#EF4444'
  },

  // Alertas
  alerts: {
    critical: '#DC2626',
    high: '#EF4444',
    warning: '#F59E0B',
    medium: '#F59E0B',
    info: '#3B82F6',
    low: '#3B82F6'
  },

  // Ocupación
  occupation: {
    underutilized: '#FEF3C7',
    normal: '#10B981',
    high: '#F59E0B',
    overloaded: '#EF4444'
  }
};

export const getOccupationColor = (rate) => {
  if (rate > 100) return COLORS.occupation.overloaded;
  if (rate > 80) return COLORS.occupation.high;
  if (rate > 50) return COLORS.occupation.normal;
  return COLORS.occupation.underutilized;
};

export const getHealthColor = (status) => {
  const statusLower = status.toLowerCase();
  return COLORS.health[statusLower] || COLORS.health.regular;
};

export const getAlertColor = (severity) => {
  return COLORS.alerts[severity] || COLORS.alerts.info;
};
```

---

## 📦 8. Configuración del Provider

### App.jsx
```jsx
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import DashboardExecutive from './pages/DashboardExecutive';
import FieldsPage from './pages/FieldsPage';
import AlertsPanel from './components/AlertsPanel';

// Configurar React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 2 * 60 * 1000 // 2 minutos
    }
  }
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          <Route path="/dashboard" element={<DashboardExecutive />} />
          <Route path="/fields" element={<FieldsPage />} />
          <Route path="/alerts" element={<AlertsPanel />} />
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
```

---

## ✅ Checklist de Implementación

### Fase 1: Básico (Obligatorio)
- [ ] Instalar dependencias
- [ ] Configurar `analyticsService.js`
- [ ] Crear hook `useAnalytics.js`
- [ ] Implementar componente `KPICard`
- [ ] Implementar componente `AlertCard`
- [ ] Mostrar `animal_count` en tarjetas de potreros

### Fase 2: Dashboard (Alta Prioridad)
- [ ] Implementar `DashboardExecutive`
- [ ] Agregar gráfico de dona (distribución sexo)
- [ ] Agregar gráfico de líneas (tendencias)
- [ ] Mostrar KPIs principales
- [ ] Panel de alertas críticas

### Fase 3: Módulos Específicos
- [ ] Página de Potreros con métricas
- [ ] Página de Salud con gráficos
- [ ] Página de Animales con estadísticas
- [ ] Sistema de alertas completo

---

## 🚀 Comandos Rápidos

```bash
# Iniciar el proyecto
npm install
npm start

# Probar endpoints
# Dashboard
curl -H "Authorization: Bearer $TOKEN" http://localhost:5180/api/analytics/dashboard/complete

# Potreros
curl -H "Authorization: Bearer $TOKEN" http://localhost:5180/api/fields

# Alertas
curl -H "Authorization: Bearer $TOKEN" http://localhost:5180/api/analytics/alerts
```

---

## 📞 Soporte

Si tienes dudas:
1. Revisa `ANALYTICS_API_DOCUMENTATION.md` para detalles de endpoints
2. Revisa `GRAFICOS_RECOMENDADOS.md` para diseños visuales
3. Revisa `RESUMEN_IMPLEMENTACION_ANALYTICS.md` para contexto general

**¡Todo el backend está listo! Solo necesitas consumir los endpoints.** 🎉
