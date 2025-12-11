# Documentación de la Corrección del Buscador por Fechas

## Problema Original

El buscador por fechas tenía los siguientes problemas:

1. **Búsqueda demasiado amplia**: Al buscar "2025", encontraba registros que coincidieran con CUALQUIERA de estas condiciones:
   - Tener "2025" en cualquier campo de texto
   - Tener ID = 2025
   - Tener año 2025 en cualquier campo de fecha

2. **Resultados inesperados**: Mostraba registros que no tenían relación con la búsqueda de fechas

3. **Falta de control**: No había forma de especificar si querías buscar solo en fechas, solo en texto, o en todos los campos

## Solución Implementada

### 1. Lógica de Búsqueda Separada

Se modificó el método `get_namespace_query()` en `app/models/base_model.py` para separar la lógica de búsqueda:

- **Búsqueda por fechas**: Solo busca en campos de tipo Date/DateTime
- **Búsqueda por texto**: Solo busca en campos de texto y ID
- **Búsqueda combinada**: Busca en todos los campos (opcional)

### 2. Nuevo Parámetro `search_type`

Se agregó un nuevo parámetro opcional `search_type` con las siguientes opciones:

#### `search_type='auto'` (default)
- Detecta automáticamente si el término de búsqueda es una fecha
- Si es fecha: busca solo en campos de fecha
- Si no es fecha: busca solo en campos de texto e ID

#### `search_type='dates'`
- Fuerza la búsqueda solo en campos de fecha (Date/DateTime)
- Ignora campos de texto e ID

#### `search_type='text'`
- Fuerza la búsqueda solo en campos de texto e ID
- Ignora campos de fecha

#### `search_type='all'`
- Busca en todos los campos (comportamiento original)
- Combina búsqueda de texto, ID, y fechas con OR

### 3. Formatos de Fecha Soportados

El sistema reconoce automáticamente estos formatos:

- **Año**: `2025` (4 dígitos)
- **Año-Mes**: `2024-12` o `2024/12`
- **Fecha completa**: 
  - `2024-12-25` (ISO)
  - `25/12/2024` (Europeo)
  - `2024/12/25` (Americano)
- **DateTime completo**:
  - `2024-12-25T14:30:00`
  - `2024-12-25 14:30:00`
  - `2024-12-25 14:30`
  - `25/12/2024 14:30:00`

## Ejemplos de Uso

### Búsqueda por Año (2025)
```bash
# Solo registros con fechas en 2025
GET /api/v1/animals/?search=2025

# Explícitamente solo en fechas
GET /api/v1/animals/?search=2025&search_type=dates
```

### Búsqueda por Texto "2025"
```bash
# Solo registros con "2025" en campos de texto o ID=2025
GET /api/v1/animals/?search=2025&search_type=text
```

### Búsqueda Combinada (comportamiento anterior)
```bash
# Busca en todos los campos (texto, ID, y fechas)
GET /api/v1/animals/?search=2025&search_type=all
```

### Búsqueda por Mes
```bash
# Registros de diciembre 2024
GET /api/v1/treatments/?search=2024-12
```

### Búsqueda por Fecha Específica
```bash
# Registros del 25 de diciembre 2024
GET /api/v1/vaccinations/?search=25/12/2024
```

## Cambios en el Código

### 1. `app/models/base_model.py`

- **Firma del método**: Se agregó el parámetro `search_type='auto'`
- **Lógica reestructurada**: Separación clara entre tipos de búsqueda
- **Detección de fechas**: Mejorada para evitar falsos positivos

### 2. `app/utils/namespace_helpers.py`

- **Extracción de parámetros**: Se agrega `search_type` desde los query params
- **Paso del parámetro**: Se pasa `search_type` al método `get_namespace_query()`

## Impacto en la API

### Backward Compatibility

- **Totalmente compatible**: Las URLs existentes siguen funcionando igual
- **Comportamiento por defecto**: `search_type='auto'` mejora la precisión sin romper el flujo existente

### Nuevas Posibilidades

- **Búsqueda más precisa**: Los usuarios ahora pueden controlar el alcance de la búsqueda
- **Menos falsos positivos**: Las búsquedas de fechas ya no incluyen coincidencias de texto
- **Flexibilidad**: Se puede elegir el tipo de búsqueda según la necesidad

## Testing

Se crearon scripts de prueba para verificar:

1. **Detección correcta de fechas**: Verificar que los formatos se reconocen adecuadamente
2. **Separación de lógica**: Confirmar que cada tipo de búsqueda funciona independientemente
3. **Compatibilidad**: Asegurar que el comportamiento anterior sigue disponible con `search_type='all'`

## Recomendaciones de Uso

### Para Búsquedas de Fechas
- Usar `search=2025` para buscar registros de ese año
- Usar `search=2024-12` para buscar registros de ese mes
- Usar `search=25/12/2024` para buscar registros de esa fecha específica

### Para Búsquedas de Texto
- Usar `search=2025&search_type=text` si necesitas encontrar "2025" en campos de texto
- Usar `search=vaca` para buscar texto (el `search_type='auto'` lo detectará automáticamente)

### Para Búsquedas Generales
- Usar `search=termino&search_type=all` si necesitas el comportamiento original

## Resumen

La corrección soluciona el problema principal donde las búsquedas por fechas devolvían resultados irrelevantes de campos de texto. Ahora los usuarios tienen control total sobre el alcance de la búsqueda, manteniendo la compatibilidad con el código existente.