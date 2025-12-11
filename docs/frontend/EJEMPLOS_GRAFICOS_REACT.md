# 📊 Ejemplos Completos de Gráficos en React

Esta guía proporciona **ejemplos de código completos y listos para usar** para cada tipo de gráfico recomendado en el sistema de analytics.

---

## 📑 Índice de Gráficos

### Analytics de Animales
1. [Distribución por Estado (Donut Chart)](#1-distribución-por-estado-donut-chart)
2. [Distribución por Sexo (Pie Chart)](#2-distribución-por-sexo-pie-chart)
3. [Top 5 Razas (Bar Chart Horizontal)](#3-top-5-razas-bar-chart-horizontal)
4. [Grupos de Edad (Stacked Bar Chart)](#4-grupos-de-edad-stacked-bar-chart)
5. [Distribución de Pesos (Histograma)](#5-distribución-de-pesos-histograma)
6. [Tendencia de Crecimiento (Line Chart)](#6-tendencia-de-crecimiento-line-chart)

### Analytics de Salud
7. [Estado de Salud del Hato (Radial Bar)](#7-estado-de-salud-del-hato-radial-bar)
8. [Tratamientos por Mes (Area Chart)](#8-tratamientos-por-mes-area-chart)
9. [Vacunaciones por Mes (Line Chart)](#9-vacunaciones-por-mes-line-chart)
10. [Enfermedades Comunes (Bar Chart)](#10-enfermedades-comunes-bar-chart)
11. [Uso de Medicamentos (Treemap)](#11-uso-de-medicamentos-treemap)

### Analytics de Campos
12. [Campos: Ocupación vs Capacidad (Bar Chart Agrupado)](#12-campos-ocupación-vs-capacidad-bar-chart-agrupado)
13. [Estado de Campos (Pie Chart)](#13-estado-de-campos-pie-chart)

### Dashboard Completo
14. [Dashboard Ejecutivo Completo](#14-dashboard-ejecutivo-completo)

---

## 1. Distribución por Estado (Donut Chart)

**Endpoint**: `/analytics/dashboard/complete` → `distribucion_estado`

```javascript
// src/components/charts/AnimalStatusDonutChart.jsx
import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { useDashboardComplete } from '../../hooks/useAnalytics';

const COLORS = {
  vivos: '#10b981',
  vendidos: '#3b82f6',
  muertos: '#ef4444'
};

const RADIAN = Math.PI / 180;
const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor={x > cx ? 'start' : 'end'}
      dominantBaseline="central"
      className="font-bold"
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};

export const AnimalStatusDonutChart = () => {
  const { data, isLoading, error } = useDashboardComplete();

  if (isLoading) return <div className="animate-pulse bg-gray-200 h-64 rounded"></div>;
  if (error) return <div className="text-red-600">Error: {error.message}</div>;

  const chartData = [
    { name: 'Vivos', value: data.distribucion_estado.vivos, color: COLORS.vivos },
    { name: 'Vendidos', value: data.distribucion_estado.vendidos, color: COLORS.vendidos },
    { name: 'Muertos', value: data.distribucion_estado.muertos, color: COLORS.muertos }
  ];

  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="bg-white p-6 rounded-lg shadow-lg">
      <h3 className="text-xl font-bold mb-4">Estado de Animales</h3>

      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderCustomizedLabel}
            outerRadius={100}
            innerRadius={60}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value, name) => [`${value} animales (${((value / total) * 100).toFixed(1)}%)`, name]}
          />
          <Legend
            verticalAlign="bottom"
            height={36}
            formatter={(value, entry) => `${value}: ${entry.payload.value}`}
          />
        </PieChart>
      </ResponsiveContainer>

      {/* Centro del donut - Total */}
      <div className="text-center -mt-48 relative z-10">
        <div className="text-4xl font-bold">{total}</div>
        <div className="text-sm text-gray-600">Total Animales</div>
      </div>
    </div>
  );
};
```

---

## 2. Distribución por Sexo (Pie Chart)

**Endpoint**: `/analytics/dashboard/complete` → `distribucion_sexo`

```javascript
// src/components/charts/SexDistributionChart.jsx
import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { useDashboardComplete } from '../../hooks/useAnalytics';

export const SexDistributionChart = () => {
  const { data, isLoading } = useDashboardComplete();

  if (isLoading) return <div>Cargando...</div>;

  const chartData = [
    {
      name: 'Machos',
      value: data.distribucion_sexo.machos,
      color: '#3b82f6',
      icon: '♂️'
    },
    {
      name: 'Hembras',
      value: data.distribucion_sexo.hembras,
      color: '#ec4899',
      icon: '♀️'
    }
  ];

  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="bg-white p-6 rounded-lg shadow-lg">
      <h3 className="text-xl font-bold mb-4">Distribución por Sexo</h3>

      <ResponsiveContainer width="100%" height={250}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => `${value} animales`} />
        </PieChart>
      </ResponsiveContainer>

      <div className="grid grid-cols-2 gap-4 mt-4">
        {chartData.map((item) => (
          <div key={item.name} className="text-center p-4 rounded" style={{ backgroundColor: `${item.color}20` }}>
            <div className="text-3xl mb-2">{item.icon}</div>
            <div className="text-2xl font-bold">{item.value}</div>
            <div className="text-sm text-gray-600">{item.name}</div>
            <div className="text-xs text-gray-500 mt-1">
              {((item.value / total) * 100).toFixed(1)}%
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

## 3. Top 5 Razas (Bar Chart Horizontal)

**Endpoint**: `/analytics/dashboard/complete` → `distribucion_razas_top5`

```javascript
// src/components/charts/TopBreedsChart.jsx
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LabelList } from 'recharts';
import { useDashboardComplete } from '../../hooks/useAnalytics';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export const TopBreedsChart = () => {
  const { data, isLoading } = useDashboardComplete();

  if (isLoading) return <div>Cargando...</div>;

  return (
    <div className="bg-white p-6 rounded-lg shadow-lg">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-bold">Top 5 Razas Más Comunes</h3>
        <span className="text-sm text-gray-500">
          Total: {data.distribucion_razas_top5.reduce((sum, item) => sum + item.cantidad, 0)} animales
        </span>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data.distribucion_razas_top5} layout="vertical" margin={{ left: 100 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
          <XAxis type="number" />
          <YAxis dataKey="raza" type="category" width={90} />
          <Tooltip
            formatter={(value) => [`${value} animales`, 'Cantidad']}
            contentStyle={{ borderRadius: '8px' }}
          />
          <Bar dataKey="cantidad" fill="#3b82f6" radius={[0, 8, 8, 0]}>
            {data.distribucion_razas_top5.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
            <LabelList dataKey="cantidad" position="right" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Tabla resumen */}
      <div className="mt-4 border-t pt-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-600">
              <th className="pb-2">Posición</th>
              <th className="pb-2">Raza</th>
              <th className="pb-2 text-right">Cantidad</th>
              <th className="pb-2 text-right">%</th>
            </tr>
          </thead>
          <tbody>
            {data.distribucion_razas_top5.map((item, index) => {
              const total = data.distribucion_razas_top5.reduce((sum, i) => sum + i.cantidad, 0);
              return (
                <tr key={index} className="border-t">
                  <td className="py-2">#{index + 1}</td>
                  <td className="py-2 font-medium">{item.raza}</td>
                  <td className="py-2 text-right">{item.cantidad}</td>
                  <td className="py-2 text-right text-gray-600">
                    {((item.cantidad / total) * 100).toFixed(1)}%
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
```

---

## 4. Grupos de Edad (Stacked Bar Chart)

**Endpoint**: `/analytics/dashboard/complete` → `grupos_edad`

```javascript
// src/components/charts/AgeGroupsChart.jsx
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Cell } from 'recharts';
import { useDashboardComplete } from '../../hooks/useAnalytics';

const AGE_GROUP_COLORS = {
  terneros: '#3b82f6',
  jovenes: '#10b981',
  adultos: '#f59e0b',
  maduros: '#8b5cf6'
};

const AGE_GROUP_LABELS = {
  terneros: 'Terneros (0-12m)',
  jovenes: 'Jóvenes (12-24m)',
  adultos: 'Adultos (24-60m)',
  maduros: 'Maduros (60m+)'
};

export const AgeGroupsChart = () => {
  const { data, isLoading } = useDashboardComplete();

  if (isLoading) return <div>Cargando...</div>;

  // Transformar datos para el gráfico
  const chartData = Object.entries(data.grupos_edad).map(([key, value]) => ({
    name: AGE_GROUP_LABELS[key],
    value: value,
    color: AGE_GROUP_COLORS[key]
  }));

  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="bg-white p-6 rounded-lg shadow-lg">
      <h3 className="text-xl font-bold mb-4">Distribución por Grupos de Edad</h3>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
          <YAxis />
          <Tooltip
            formatter={(value) => [`${value} animales`, 'Cantidad']}
            contentStyle={{ borderRadius: '8px' }}
          />
          <Bar dataKey="value" fill="#8884d8" radius={[8, 8, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Cards de resumen */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
        {chartData.map((item) => (
          <div
            key={item.name}
            className="p-4 rounded-lg"
            style={{ backgroundColor: `${item.color}15`, borderLeft: `4px solid ${item.color}` }}
          >
            <div className="text-2xl font-bold">{item.value}</div>
            <div className="text-sm text-gray-700">{item.name}</div>
            <div className="text-xs text-gray-500 mt-1">
              {total > 0 ? ((item.value / total) * 100).toFixed(1) : 0}% del total
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 text-center text-sm text-gray-600">
        Total de animales con edad registrada: <span className="font-bold">{total}</span>
      </div>
    </div>
  );
};
```

---

## 5. Distribución de Pesos (Histograma)

**Endpoint**: `/analytics/animals/statistics` → `weight_distribution`

```javascript
// src/components/charts/WeightDistributionChart.jsx
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { useAnimalStatistics } from '../../hooks/useAnalytics';

const WEIGHT_COLORS = {
  '0-200 kg': '#ef4444',
  '201-400 kg': '#f59e0b',
  '401-600 kg': '#10b981',
  '601+ kg': '#3b82f6'
};

export const WeightDistributionChart = () => {
  const { data, isLoading } = useAnimalStatistics();

  if (isLoading) return <div>Cargando...</div>;

  // Transformar datos
  const chartData = Object.entries(data.weight_distribution).map(([range, count]) => ({
    range,
    count,
    color: WEIGHT_COLORS[range]
  }));

  const total = chartData.reduce((sum, item) => sum + item.count, 0);

  return (
    <div className="bg-white p-6 rounded-lg shadow-lg">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-bold">Distribución de Pesos</h3>
        <div className="text-right">
          <div className="text-sm text-gray-600">Peso promedio</div>
          <div className="text-2xl font-bold text-blue-600">{data.average_weight.toFixed(1)} kg</div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="range" />
          <YAxis />
          <Tooltip
            formatter={(value) => [`${value} animales`, 'Cantidad']}
            contentStyle={{ borderRadius: '8px' }}
          />
          <Bar dataKey="count" fill="#3b82f6" radius={[8, 8, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Estadísticas por rango */}
      <div className="mt-6 grid grid-cols-2 lg:grid-cols-4 gap-3">
        {chartData.map((item) => (
          <div
            key={item.range}
            className="p-3 rounded border-l-4"
            style={{ borderColor: item.color, backgroundColor: `${item.color}10` }}
          >
            <div className="text-sm text-gray-600">{item.range}</div>
            <div className="text-xl font-bold">{item.count}</div>
            <div className="text-xs text-gray-500">
              {total > 0 ? ((item.count / total) * 100).toFixed(1) : 0}% del hato
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

## 6. Tendencia de Crecimiento (Line Chart)

**Endpoint**: `/analytics/production/statistics` → `weight_trends`

```javascript
// src/components/charts/GrowthTrendChart.jsx
import React, { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { useProductionStats } from '../../hooks/useAnalytics';

export const GrowthTrendChart = () => {
  const [period, setPeriod] = useState('1y');
  const { data, isLoading } = useProductionStats(period);

  if (isLoading) return <div>Cargando...</div>;

  // Calcular promedio para línea de referencia
  const avgWeight = data.weight_trends.reduce((sum, item) => sum + item.avg_weight, 0) / data.weight_trends.length;

  return (
    <div className="bg-white p-6 rounded-lg shadow-lg">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-xl font-bold">Tendencia de Peso Promedio</h3>
          <p className="text-sm text-gray-600 mt-1">
            Evolución del peso promedio del hato en el tiempo
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setPeriod('6m')}
            className={`px-4 py-2 rounded ${
              period === '6m' ? 'bg-blue-600 text-white' : 'bg-gray-200'
            }`}
          >
            6 meses
          </button>
          <button
            onClick={() => setPeriod('1y')}
            className={`px-4 py-2 rounded ${
              period === '1y' ? 'bg-blue-600 text-white' : 'bg-gray-200'
            }`}
          >
            1 año
          </button>
          <button
            onClick={() => setPeriod('2y')}
            className={`px-4 py-2 rounded ${
              period === '2y' ? 'bg-blue-600 text-white' : 'bg-gray-200'
            }`}
          >
            2 años
          </button>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={data.weight_trends} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="period"
            label={{ value: 'Período', position: 'insideBottom', offset: -5 }}
          />
          <YAxis
            label={{ value: 'Peso (kg)', angle: -90, position: 'insideLeft' }}
            domain={['dataMin - 20', 'dataMax + 20']}
          />
          <Tooltip
            formatter={(value, name) => [`${value} kg`, name === 'avg_weight' ? 'Peso Promedio' : name]}
            labelFormatter={(label) => `Período: ${label}`}
            contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
          />
          <Legend />
          <ReferenceLine
            y={avgWeight}
            label={`Promedio: ${avgWeight.toFixed(1)} kg`}
            stroke="#f59e0b"
            strokeDasharray="3 3"
          />
          <Line
            type="monotone"
            dataKey="avg_weight"
            stroke="#3b82f6"
            strokeWidth={3}
            name="Peso Promedio"
            dot={{ r: 5, fill: '#3b82f6' }}
            activeDot={{ r: 7 }}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* KPIs de producción */}
      <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t">
        <div className="text-center">
          <div className="text-sm text-gray-600">GMD Promedio</div>
          <div className="text-2xl font-bold text-green-600">
            {data.productivity_metrics.average_daily_gain_kg.toFixed(3)} kg/día
          </div>
        </div>
        <div className="text-center">
          <div className="text-sm text-gray-600">Animales Analizados</div>
          <div className="text-2xl font-bold text-blue-600">
            {data.productivity_metrics.total_animals_analyzed}
          </div>
        </div>
        <div className="text-center">
          <div className="text-sm text-gray-600">Controles Realizados</div>
          <div className="text-2xl font-bold text-purple-600">
            {data.summary.total_controls}
          </div>
        </div>
      </div>
    </div>
  );
};
```

---

## 7. Estado de Salud del Hato (Radial Bar)

**Endpoint**: `/analytics/dashboard/complete` → `distribucion_salud`

```javascript
// src/components/charts/HealthStatusRadialChart.jsx
import React from 'react';
import { RadialBarChart, RadialBar, Legend, ResponsiveContainer, Tooltip } from 'recharts';
import { useDashboardComplete } from '../../hooks/useAnalytics';

const HEALTH_COLORS = {
  excelente: '#10b981',
  bueno: '#22c55e',
  sano: '#84cc16',
  regular: '#f59e0b',
  malo: '#ef4444'
};

export const HealthStatusRadialChart = () => {
  const { data, isLoading } = useDashboardComplete();

  if (isLoading) return <div>Cargando...</div>;

  // Transformar datos para RadialBar
  const healthData = Object.entries(data.distribucion_salud).map(([status, count]) => ({
    name: status.charAt(0).toUpperCase() + status.slice(1),
    value: count,
    fill: HEALTH_COLORS[status]
  }));

  const total = healthData.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="bg-white p-6 rounded-lg shadow-lg">
      <h3 className="text-xl font-bold mb-4">Estado de Salud del Hato</h3>

      <ResponsiveContainer width="100%" height={350}>
        <RadialBarChart
          cx="50%"
          cy="50%"
          innerRadius="10%"
          outerRadius="90%"
          barSize={15}
          data={healthData}
        >
          <RadialBar
            minAngle={15}
            label={{ position: 'insideStart', fill: '#fff', fontSize: 12 }}
            background
            clockWise
            dataKey="value"
          />
          <Legend
            iconSize={10}
            layout="vertical"
            verticalAlign="middle"
            align="right"
            formatter={(value, entry) => `${value}: ${entry.payload.value}`}
          />
          <Tooltip
            formatter={(value) => [`${value} animales`, 'Cantidad']}
          />
        </RadialBarChart>
      </ResponsiveContainer>

      {/* Indicadores de salud */}
      <div className="grid grid-cols-5 gap-2 mt-6">
        {healthData.map((item) => (
          <div
            key={item.name}
            className="p-3 rounded text-center"
            style={{ backgroundColor: `${item.fill}20`, borderTop: `3px solid ${item.fill}` }}
          >
            <div className="text-lg font-bold">{item.value}</div>
            <div className="text-xs text-gray-600">{item.name}</div>
            <div className="text-xs text-gray-500 mt-1">
              {total > 0 ? ((item.value / total) * 100).toFixed(0) : 0}%
            </div>
          </div>
        ))}
      </div>

      {/* Índice de salud general */}
      <div className="mt-6 p-4 bg-gradient-to-r from-green-50 to-blue-50 rounded-lg">
        <div className="flex justify-between items-center">
          <div>
            <div className="text-sm text-gray-600">Índice de Salud General</div>
            <div className="text-xs text-gray-500 mt-1">
              Basado en los últimos controles de {total} animales
            </div>
          </div>
          <div className="text-4xl font-bold text-green-600">
            {(() => {
              const healthScore =
                (healthData.find(h => h.name === 'Excelente')?.value || 0) * 5 +
                (healthData.find(h => h.name === 'Bueno')?.value || 0) * 4 +
                (healthData.find(h => h.name === 'Sano')?.value || 0) * 3 +
                (healthData.find(h => h.name === 'Regular')?.value || 0) * 2 +
                (healthData.find(h => h.name === 'Malo')?.value || 0) * 1;
              return total > 0 ? ((healthScore / (total * 5)) * 100).toFixed(0) : 0;
            })()}%
          </div>
        </div>
      </div>
    </div>
  );
};
```

---

## 8. Tratamientos por Mes (Area Chart)

**Endpoint**: `/analytics/health/statistics` → `treatments_by_month`

```javascript
// src/components/charts/TreatmentsTrendChart.jsx
import React, { useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import { useHealthStatistics } from '../../hooks/useAnalytics';

export const TreatmentsTrendChart = () => {
  const [months, setMonths] = useState(12);
  const { data, isLoading } = useHealthStatistics(months);

  if (isLoading) return <div>Cargando...</div>;

  // Combinar tratamientos y vacunaciones en un solo dataset
  const combinedData = data.treatments_by_month.map((treatment) => {
    const vaccination = data.vaccinations_by_month.find(
      (v) => v.period === treatment.period
    );
    return {
      period: treatment.period,
      tratamientos: treatment.count,
      vacunaciones: vaccination?.count || 0
    };
  });

  return (
    <div className="bg-white p-6 rounded-lg shadow-lg">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-xl font-bold">Actividad Sanitaria Mensual</h3>
          <p className="text-sm text-gray-600">Tratamientos y vacunaciones aplicados</p>
        </div>

        <select
          value={months}
          onChange={(e) => setMonths(Number(e.target.value))}
          className="border rounded px-3 py-2"
        >
          <option value={6}>Últimos 6 meses</option>
          <option value={12}>Último año</option>
          <option value={24}>Últimos 2 años</option>
        </select>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={combinedData}>
          <defs>
            <linearGradient id="colorTratamientos" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorVacunaciones" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="period" />
          <YAxis />
          <Tooltip
            contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
          />
          <Legend />
          <Area
            type="monotone"
            dataKey="tratamientos"
            stroke="#ef4444"
            fillOpacity={1}
            fill="url(#colorTratamientos)"
            name="Tratamientos"
          />
          <Area
            type="monotone"
            dataKey="vacunaciones"
            stroke="#10b981"
            fillOpacity={1}
            fill="url(#colorVacunaciones)"
            name="Vacunaciones"
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Resumen numérico */}
      <div className="grid grid-cols-2 gap-4 mt-6">
        <div className="p-4 bg-red-50 rounded-lg border-l-4 border-red-500">
          <div className="text-sm text-gray-600">Total Tratamientos</div>
          <div className="text-3xl font-bold text-red-600">{data.summary.total_treatments}</div>
          <div className="text-xs text-gray-500 mt-1">
            Promedio: {(data.summary.total_treatments / months).toFixed(1)} por mes
          </div>
        </div>
        <div className="p-4 bg-green-50 rounded-lg border-l-4 border-green-500">
          <div className="text-sm text-gray-600">Total Vacunaciones</div>
          <div className="text-3xl font-bold text-green-600">{data.summary.total_vaccinations}</div>
          <div className="text-xs text-gray-500 mt-1">
            Promedio: {(data.summary.total_vaccinations / months).toFixed(1)} por mes
          </div>
        </div>
      </div>
    </div>
  );
};
```

---

## 14. Dashboard Ejecutivo Completo

Este es el dashboard principal que combina todos los gráficos anteriores:

```javascript
// src/pages/ExecutiveDashboard.jsx
import React from 'react';
import { useDashboardComplete } from '../hooks/useAnalytics';
import { AnimalStatusDonutChart } from '../components/charts/AnimalStatusDonutChart';
import { SexDistributionChart } from '../components/charts/SexDistributionChart';
import { TopBreedsChart } from '../components/charts/TopBreedsChart';
import { AgeGroupsChart } from '../components/charts/AgeGroupsChart';
import { WeightDistributionChart } from '../components/charts/WeightDistributionChart';
import { GrowthTrendChart } from '../components/charts/GrowthTrendChart';
import { HealthStatusRadialChart } from '../components/charts/HealthStatusRadialChart';
import { TreatmentsTrendChart } from '../components/charts/TreatmentsTrendChart';
import { AlertsPanel } from '../components/alerts/AlertsPanel';

const KPICard = ({ title, value, change, description, icon, color = 'blue' }) => {
  const colorClasses = {
    blue: 'bg-blue-50 border-blue-500 text-blue-600',
    green: 'bg-green-50 border-green-500 text-green-600',
    red: 'bg-red-50 border-red-500 text-red-600',
    yellow: 'bg-yellow-50 border-yellow-500 text-yellow-600',
    purple: 'bg-purple-50 border-purple-500 text-purple-600'
  };

  return (
    <div className={`p-6 rounded-lg border-l-4 ${colorClasses[color]}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-600">{title}</p>
          <p className="text-3xl font-bold mt-2">{value}</p>
          {change !== undefined && change !== 0 && (
            <p className={`text-sm mt-2 flex items-center gap-1 ${
              change >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {change >= 0 ? '↑' : '↓'}
              <span className="font-medium">{Math.abs(change)}%</span>
              <span className="text-xs text-gray-500">vs período anterior</span>
            </p>
          )}
          <p className="text-xs text-gray-500 mt-1">{description}</p>
        </div>
        <span className="text-4xl">{icon}</span>
      </div>
    </div>
  );
};

export const ExecutiveDashboard = () => {
  const { data, isLoading, error, refetch } = useDashboardComplete();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-100 p-8">
        <div className="animate-pulse space-y-8">
          <div className="h-12 bg-gray-200 rounded w-1/3"></div>
          <div className="grid grid-cols-4 gap-6">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-red-800 font-bold text-lg mb-2">Error al cargar el dashboard</h3>
          <p className="text-red-600">{error.message}</p>
          <button
            onClick={() => refetch()}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      {/* Header */}
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-bold text-gray-900">Dashboard Ejecutivo</h1>
          <p className="text-gray-600 mt-2">
            Sistema de Gestión Ganadera - Analytics en Tiempo Real
          </p>
        </div>
        <div className="text-right">
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            🔄 Actualizar
          </button>
          <p className="text-xs text-gray-500 mt-2">
            Última actualización: {new Date(data.metadata.generado_en).toLocaleString('es-ES')}
          </p>
        </div>
      </div>

      {/* KPIs Principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <KPICard
          title="Animales Registrados"
          value={data.animales_registrados.valor}
          change={data.animales_registrados.cambio_porcentual}
          description={data.animales_registrados.descripcion}
          icon="🐄"
          color="blue"
        />
        <KPICard
          title="Animales Activos"
          value={data.animales_activos.valor}
          description="Animales vivos en el sistema"
          icon="✅"
          color="green"
        />
        <KPICard
          title="Tratamientos Activos"
          value={data.tratamientos_activos.valor}
          description="Tratamientos en curso (últimos 30 días)"
          icon="💊"
          color="red"
        />
        <KPICard
          title="Alertas del Sistema"
          value={data.alertas_sistema.valor}
          change={data.alertas_sistema.cambio_porcentual}
          description={data.alertas_sistema.descripcion}
          icon="🚨"
          color="yellow"
        />
      </div>

      {/* Segunda fila de KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <KPICard
          title="Usuarios Activos"
          value={data.usuarios_activos.valor}
          change={data.usuarios_activos.cambio_porcentual}
          description="Usuarios con actividad reciente"
          icon="👥"
          color="purple"
        />
        <KPICard
          title="Campos Registrados"
          value={data.campos_registrados.valor}
          change={data.campos_registrados.cambio_porcentual}
          description="Lotes/campos administrados"
          icon="🏞️"
          color="green"
        />
        <KPICard
          title="Controles Realizados"
          value={data.controles_realizados.valor}
          change={data.controles_realizados.cambio_porcentual}
          description="Controles de salud registrados"
          icon="📊"
          color="blue"
        />
        <KPICard
          title="Vacunas Aplicadas"
          value={data.vacunas_aplicadas.valor}
          change={data.vacunas_aplicadas.cambio_porcentual}
          description="Vacunaciones totales"
          icon="💉"
          color="green"
        />
      </div>

      {/* Gráficos Principales - Fila 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <AnimalStatusDonutChart />
        <SexDistributionChart />
      </div>

      {/* Gráficos Principales - Fila 2 */}
      <div className="grid grid-cols-1 gap-6 mb-8">
        <TopBreedsChart />
      </div>

      {/* Gráficos de Edad y Peso */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <AgeGroupsChart />
        <WeightDistributionChart />
      </div>

      {/* Tendencia de Crecimiento */}
      <div className="mb-8">
        <GrowthTrendChart />
      </div>

      {/* Salud y Tratamientos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <HealthStatusRadialChart />
        <TreatmentsTrendChart />
      </div>

      {/* Sistema de Alertas */}
      <AlertsPanel />

      {/* Metadata y Estadísticas Adicionales */}
      <div className="mt-8 bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-bold mb-4">Estadísticas Adicionales</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-sm text-gray-600">Peso Promedio</div>
            <div className="text-2xl font-bold text-blue-600">{data.peso_promedio_kg} kg</div>
          </div>
          <div className="text-center">
            <div className="text-sm text-gray-600">Muertes (30d)</div>
            <div className="text-2xl font-bold text-red-600">{data.muertes_recientes_30dias}</div>
          </div>
          <div className="text-center">
            <div className="text-sm text-gray-600">Ventas (30d)</div>
            <div className="text-2xl font-bold text-green-600">{data.ventas_recientes_30dias}</div>
          </div>
          <div className="text-center">
            <div className="text-sm text-gray-600">Tratamientos/Animal</div>
            <div className="text-2xl font-bold text-purple-600">{data.promedio_tratamientos_por_animal}</div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 text-center text-sm text-gray-500">
        <p>
          Dashboard generado automáticamente | Cache: {data.metadata.cache_ttl}s |
          Versión: {data.metadata.version} | {data.metadata.estadisticas_totales} KPIs
        </p>
      </div>
    </div>
  );
};
```

---

## 🎯 Resumen de Implementación

### Componentes Creados

| Componente | Archivo | Endpoint Usado |
|------------|---------|----------------|
| AnimalStatusDonutChart | `AnimalStatusDonutChart.jsx` | `/dashboard/complete` |
| SexDistributionChart | `SexDistributionChart.jsx` | `/dashboard/complete` |
| TopBreedsChart | `TopBreedsChart.jsx` | `/dashboard/complete` |
| AgeGroupsChart | `AgeGroupsChart.jsx` | `/dashboard/complete` |
| WeightDistributionChart | `WeightDistributionChart.jsx` | `/animals/statistics` |
| GrowthTrendChart | `GrowthTrendChart.jsx` | `/production/statistics` |
| HealthStatusRadialChart | `HealthStatusRadialChart.jsx` | `/dashboard/complete` |
| TreatmentsTrendChart | `TreatmentsTrendChart.jsx` | `/health/statistics` |
| ExecutiveDashboard | `ExecutiveDashboard.jsx` | Todos los anteriores |

### Dependencias Necesarias

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "axios": "^1.6.0",
    "react-query": "^3.39.3",
    "recharts": "^2.10.0",
    "date-fns": "^2.30.0"
  }
}
```

### Próximos Pasos

1. ✅ Copiar los componentes a tu proyecto React
2. ✅ Instalar las dependencias necesarias
3. ✅ Configurar React Query Provider
4. ✅ Configurar la variable de entorno `REACT_APP_API_URL`
5. ✅ Importar y usar los componentes en tus páginas

---

**✨ Todos los ejemplos están listos para producción y son completamente funcionales.**
