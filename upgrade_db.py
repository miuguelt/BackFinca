import os
import sys
import logging
from dotenv import load_dotenv
from alembic.config import Config
from alembic import command
from sqlalchemy import inspect, text

def _mask_uri(uri: str) -> str:
    try:
        if "://" not in uri:
            return uri
        scheme, rest = uri.split("://", 1)
        if "@" in rest and ":" in rest.split("@", 1)[0]:
            creds, hostpart = rest.split("@", 1)
            user = creds.split(":", 1)[0]
            return f"{scheme}://{user}:***@{hostpart}"
        return uri
    except Exception:
        return uri

def main():
    load_dotenv(override=True)

    flask_env = os.getenv("FLASK_ENV") or "development"
    os.environ["FLASK_ENV"] = flask_env

    jwt = os.getenv("JWT_SECRET_KEY")
    db_uri = os.getenv("SQLALCHEMY_DATABASE_URI")
    if not jwt or not db_uri:
        print("ERROR: Faltan variables requeridas: JWT_SECRET_KEY y/o SQLALCHEMY_DATABASE_URI")
        sys.exit(1)

    print(f"Entorno: {flask_env}")
    print(f"Base de datos: {_mask_uri(db_uri)}")

    from app import create_app, db
    app = create_app(flask_env)

    with app.app_context():
        try:
            db.session.execute(text("SELECT 1"))
            print("Conexión a la base de datos OK")
        except Exception as e:
            print(f"ERROR: Conexión a la base de datos falló: {e}")
            sys.exit(1)

        cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
        try:
            command.upgrade(cfg, "head")
            print("Upgrade ejecutado hasta head")
        except Exception as e:
            print(f"ERROR: Falló upgrade: {e}")
            sys.exit(1)

        try:
            rev = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
            print(f"Revisión actual: {rev}")
        except Exception as e:
            print(f"ADVERTENCIA: No se pudo leer alembic_version: {e}")

        try:
            insp = inspect(db.engine)
            required_cols = {
                "animals": [
                    ["idFather"],
                    ["idMother"],
                    ["birth_date"],
                    ["record"],
                ],
                "animal_fields": [
                    ["field_id", "removal_date"],
                    ["animal_id", "removal_date"],
                ],
                "control": [
                    ["animal_id", "health_status"],
                    ["animal_id", "checkup_date"],
                    ["created_at"],
                ],
                "user": [
                    ["identification"],
                    ["role"],
                    ["status"],
                    ["created_at"],
                ],
                "vaccinations": [
                    ["animal_id", "vaccination_date"],
                    ["created_at"],
                ],
                "treatments": [
                    ["animal_id", "treatment_date"],
                    ["created_at"],
                ],
                "activity_log": [
                    ["created_at"],
                    ["actor_id", "created_at"],
                    ["actor_id", "entity", "created_at"],
                    ["actor_id", "action", "created_at"],
                    ["actor_id", "severity", "created_at"],
                    ["actor_id", "animal_id", "created_at"],
                ],
                "activity_daily_agg": [
                    ["date"],
                    ["actor_id", "date"],
                    ["actor_id", "date", "entity"],
                ],
            }

            def table_index_columns(table):
                indexes = []
                try:
                    for ix in insp.get_indexes(table):
                        cols = ix.get("column_names") or []
                        if cols:
                            indexes.append(cols)
                except Exception:
                    pass
                try:
                    rows = db.session.execute(text(f"SHOW INDEX FROM {table}")).fetchall()
                    by_name = {}
                    for r in rows:
                        name = r._mapping.get("Key_name")
                        col = r._mapping.get("Column_name")
                        seq = r._mapping.get("Seq_in_index")
                        if name and col and seq is not None:
                            by_name.setdefault(name, {})[int(seq)] = col
                    for name, seq_map in by_name.items():
                        ordered_cols = [seq_map[i] for i in sorted(seq_map)]
                        if ordered_cols:
                            indexes.append(ordered_cols)
                except Exception:
                    pass
                return indexes

            def has_index_with_prefix(indexes, required):
                for cols in indexes:
                    if len(cols) >= len(required) and cols[:len(required)] == required:
                        return True
                return False

            total_checks = 0
            ok = 0
            missing = []
            for table, col_sets in required_cols.items():
                if not insp.has_table(table):
                    for cols in col_sets:
                        missing.append((table, ",".join(cols), "tabla_no_existe"))
                    total_checks += len(col_sets)
                    continue
                idx_cols = table_index_columns(table)
                for cols in col_sets:
                    total_checks += 1
                    if has_index_with_prefix(idx_cols, cols):
                        ok += 1
                    else:
                        missing.append((table, ",".join(cols), "no_encontrado"))
            print(f"Verificación de índices críticos (por columnas): {ok}/{total_checks} presentes")
            if missing:
                print("Faltantes:")
                for t, n, reason in missing:
                    print(f"- {t}: {n} ({reason})")
            else:
                print("Todos los índices críticos están presentes")
        except Exception as e:
            print(f"ADVERTENCIA: Falló verificación de índices: {e}")

        try:
            insp = inspect(db.engine)
            create_map = {
                ("animals", ("birth_date",)): "CREATE INDEX ix_animals_birth_date ON animals(birth_date)",
                ("animal_fields", ("field_id", "removal_date")): "CREATE INDEX idx_animal_fields_field_removal ON animal_fields(field_id, removal_date)",
                ("animal_fields", ("animal_id", "removal_date")): "CREATE INDEX ix_animal_fields_animal_removal ON animal_fields(animal_id, removal_date)",
                ("control", ("animal_id", "health_status")): "CREATE INDEX ix_control_animal_status ON control(animal_id, health_status)",
                ("user", ("role",)): "CREATE INDEX ix_user_role ON user(role)",
                ("user", ("status",)): "CREATE INDEX ix_user_status ON user(status)",
            }
            to_create = []
            for (table, cols), sql in create_map.items():
                if not insp.has_table(table):
                    continue
                rows = db.session.execute(text(f"SHOW INDEX FROM {table}")).fetchall()
                by_name = {}
                for r in rows:
                    name = r._mapping.get("Key_name")
                    col = r._mapping.get("Column_name")
                    seq = r._mapping.get("Seq_in_index")
                    if name and col and seq is not None:
                        by_name.setdefault(name, {})[int(seq)] = col
                exists = False
                for name, seq_map in by_name.items():
                    ordered = [seq_map[i] for i in sorted(seq_map)]
                    if len(ordered) >= len(cols) and ordered[:len(cols)] == list(cols):
                        exists = True
                        break
                if not exists:
                    to_create.append((table, cols, sql))
            if to_create:
                print("Creando índices críticos faltantes:")
                for table, cols, sql in to_create:
                    try:
                        db.session.execute(text(sql))
                        db.session.commit()
                        print(f"- {table}({','.join(cols)}): OK")
                    except Exception as e:
                        db.session.rollback()
                        print(f"- {table}({','.join(cols)}): ERROR {e}")
            else:
                print("No hay índices faltantes para crear")
        except Exception as e:
            print(f"ADVERTENCIA: No se pudo crear índices faltantes: {e}")

        try:
            insp = inspect(db.engine)
            required_cols = {
                "animals": [
                    ["idFather"],
                    ["idMother"],
                    ["birth_date"],
                    ["record"],
                ],
                "animal_fields": [
                    ["field_id", "removal_date"],
                    ["animal_id", "removal_date"],
                ],
                "control": [
                    ["animal_id", "health_status"],
                    ["animal_id", "checkup_date"],
                    ["created_at"],
                ],
                "user": [
                    ["identification"],
                    ["role"],
                    ["status"],
                    ["created_at"],
                ],
                "vaccinations": [
                    ["animal_id", "vaccination_date"],
                    ["created_at"],
                ],
                "treatments": [
                    ["animal_id", "treatment_date"],
                    ["created_at"],
                ],
                "activity_log": [
                    ["created_at"],
                    ["actor_id", "created_at"],
                    ["actor_id", "entity", "created_at"],
                    ["actor_id", "action", "created_at"],
                    ["actor_id", "severity", "created_at"],
                    ["actor_id", "animal_id", "created_at"],
                ],
                "activity_daily_agg": [
                    ["date"],
                    ["actor_id", "date"],
                    ["actor_id", "date", "entity"],
                ],
            }
            def table_index_columns(table):
                indexes = []
                try:
                    for ix in insp.get_indexes(table):
                        cols = ix.get("column_names") or []
                        if cols:
                            indexes.append(cols)
                except Exception:
                    pass
                try:
                    rows = db.session.execute(text(f"SHOW INDEX FROM {table}")).fetchall()
                    by_name = {}
                    for r in rows:
                        name = r._mapping.get("Key_name")
                        col = r._mapping.get("Column_name")
                        seq = r._mapping.get("Seq_in_index")
                        if name and col and seq is not None:
                            by_name.setdefault(name, {})[int(seq)] = col
                    for name, seq_map in by_name.items():
                        ordered_cols = [seq_map[i] for i in sorted(seq_map)]
                        if ordered_cols:
                            indexes.append(ordered_cols)
                except Exception:
                    pass
            def has_index_with_prefix(indexes, required):
                for cols in indexes:
                    if len(cols) >= len(required) and cols[:len(required)] == required:
                        return True
                return False
            total_checks = 0
            ok = 0
            for table, col_sets in required_cols.items():
                if not insp.has_table(table):
                    total_checks += len(col_sets)
                    continue
                idx_cols = []
                try:
                    for ix in insp.get_indexes(table):
                        cols = ix.get("column_names") or []
                        if cols:
                            idx_cols.append(cols)
                except Exception:
                    pass
                try:
                    rows = db.session.execute(text(f"SHOW INDEX FROM {table}")).fetchall()
                    by_name = {}
                    for r in rows:
                        name = r._mapping.get("Key_name")
                        col = r._mapping.get("Column_name")
                        seq = r._mapping.get("Seq_in_index")
                        if name and col and seq is not None:
                            by_name.setdefault(name, {})[int(seq)] = col
                    for name, seq_map in by_name.items():
                        ordered_cols = [seq_map[i] for i in sorted(seq_map)]
                        if ordered_cols:
                            idx_cols.append(ordered_cols)
                except Exception:
                    pass
                for cols in col_sets:
                    total_checks += 1
                    if has_index_with_prefix(idx_cols, cols):
                        ok += 1
            print(f"Verificación final (por columnas): {ok}/{total_checks} presentes")
        except Exception as e:
            print(f"ADVERTENCIA: Falló verificación final: {e}")

    print("Migraciones completadas")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
