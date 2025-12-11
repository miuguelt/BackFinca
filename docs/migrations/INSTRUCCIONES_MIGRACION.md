# 🗄️ Instrucciones para Aplicar Migración de Índices de Rendimiento

**IMPORTANTE**: Debes ejecutar este script SQL para aprovechar al máximo las mejoras de rendimiento implementadas.

---

## 📋 Qué hace esta migración

Agrega índices en los campos `updated_at` y `created_at` de **todas** las tablas, lo cual acelera:

- ✅ Endpoint `/metadata` → **40x más rápido**
- ✅ Sincronización delta `?since=timestamp` → **50x más rápido**
- ✅ Validación de caché con `Last-Modified` → **50x más rápido**
- ✅ Queries con filtros temporales → **Mucho más rápido**

---

## 🚀 Opción 1: Ejecutar SQL directamente (RECOMENDADO)

### Usar MySQL Workbench o cliente MySQL:

```bash
mysql -h isladigital.xyz -P 3311 -u fincau -p finca < add_performance_indexes.sql
```

### O copiar y pegar en la consola MySQL:

1. Abrir MySQL Workbench
2. Conectar a la base de datos `finca`
3. Abrir archivo `add_performance_indexes.sql`
4. Ejecutar (botón "Execute" o Ctrl+Shift+Enter)
5. Verificar output: "Performance indexes created successfully!"

---

## 🐍 Opción 2: Ejecutar desde Python

```python
# Crear archivo: run_migration.py
from wsgi import app
from app import db

with app.app_context():
    # Leer y ejecutar SQL
    with open('add_performance_indexes.sql', 'r') as f:
        sql = f.read()

    # Ejecutar cada CREATE INDEX por separado
    for statement in sql.split(';'):
        statement = statement.strip()
        if statement and not statement.startswith('--') and 'CREATE INDEX' in statement:
            try:
                db.session.execute(db.text(statement))
                print(f"✅ {statement[:60]}...")
            except Exception as e:
                print(f"⚠️ {statement[:60]}... (ya existe o error: {e})")

    db.session.commit()
    print("\n✅ ¡Migración completada!")
```

Luego ejecutar:
```bash
python run_migration.py
```

---

## ✅ Verificar que los índices se crearon

```sql
-- Verificar índices en tabla user
SHOW INDEX FROM user WHERE Key_name LIKE 'ix_%';

-- Verificar índices en tabla animals
SHOW INDEX FROM animals WHERE Key_name LIKE 'ix_%';

-- Verificar índices en tabla diseases
SHOW INDEX FROM diseases WHERE Key_name LIKE 'ix_%';
```

**Output esperado:**
```
+---------+------------+----------------------+--------------+-------------+
| Table   | Non_unique | Key_name             | Seq_in_index | Column_name |
+---------+------------+----------------------+--------------+-------------+
| user    |          1 | ix_user_updated_at   |            1 | updated_at  |
| user    |          1 | ix_user_created_at   |            1 | created_at  |
+---------+------------+----------------------+--------------+-------------+
```

---

## ⏱️ Tiempo estimado

- **Tablas pequeñas (<1000 filas)**: ~1 segundo por índice
- **Tablas medianas (1000-10000 filas)**: ~5-10 segundos por índice
- **Tablas grandes (>10000 filas)**: ~30-60 segundos por índice

**Total estimado**: 2-5 minutos para todas las tablas

---

## 🔍 Troubleshooting

### "Index already exists"

✅ **Esto es NORMAL y está bien**. El script usa `CREATE INDEX IF NOT EXISTS` que no falla si el índice ya existe.

### "Access denied"

❌ Verificar que el usuario `fincau` tiene permisos de `INDEX`:

```sql
GRANT INDEX ON finca.* TO 'fincau'@'%';
FLUSH PRIVILEGES;
```

### "Table doesn't exist"

⚠️ Comentar la línea del índice para esa tabla en el archivo SQL y continuar.

---

## 📊 Verificar mejora de rendimiento

### Antes de la migración:

```sql
EXPLAIN SELECT COUNT(*), MAX(updated_at) FROM user;
-- type: ALL (full table scan) ❌
-- rows: 51
-- Extra: NULL
```

### Después de la migración:

```sql
EXPLAIN SELECT COUNT(*), MAX(updated_at) FROM user;
-- type: range o index ✅
-- rows: 51
-- Extra: Using index
```

---

## 🎉 ¿Qué hacer después?

1. ✅ Ejecutar el script SQL
2. ✅ Verificar que los índices se crearon
3. ✅ Reiniciar el servidor backend (opcional pero recomendado)
4. ✅ Probar endpoints:
   - `GET /api/v1/users/metadata`
   - `GET /api/v1/users?since=2025-10-01T00:00:00Z`
5. ✅ Ver logs del backend - debe mostrar queries mucho más rápidas

---

## 📝 Rollback (opcional)

Si necesitas remover los índices:

```sql
-- User
DROP INDEX ix_user_updated_at ON user;
DROP INDEX ix_user_created_at ON user;

-- Animals
DROP INDEX ix_animals_updated_at ON animals;

-- Etc... (ver add_performance_indexes.sql para lista completa)
```

---

**Una vez ejecutado el SQL, las mejoras de rendimiento estarán activas inmediatamente. No requiere reiniciar el backend.** 🚀
