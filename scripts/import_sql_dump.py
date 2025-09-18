"""Importador de datos desde un dump SQL.

Uso básico:

  python scripts/import_sql_dump.py --file "finca (6).sql" --data-only

Opciones:
  --file PATH          Ruta al archivo .sql
  --full               Ejecuta TODO el archivo (incluye CREATE TABLE) *riesgoso si ya existen tablas*
  --data-only          (default) Solo procesa sentencias INSERT
  --force              Inserta aunque ya existan filas en la tabla
  --echo               Muestra cada sentencia ejecutada (verbose)

Notas:
 - Si tus modelos SQLAlchemy ya crearon la estructura, usa --data-only.
 - El dump tiene una base 'finca' pero tu config apunta a 'finca_db'; asegúrate de estar en la DB correcta.
 - Si hay conflictos de PK o UNIQUE se registran y se continúa (no aborta todo el proceso).
"""

from __future__ import annotations
import argparse
import os
import re
import sys
from typing import List, Tuple, Dict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))  # /scripts/..
sys.path.append(ROOT_DIR)

from app import create_app, db  # type: ignore


INSERT_REGEX = re.compile(r"^\s*INSERT\s+INTO\s+`?(?P<table>[A-Za-z0-9_]+)`?", re.IGNORECASE)
CREATE_REGEX = re.compile(r"^\s*CREATE\s+TABLE", re.IGNORECASE)
COMMENT_LINE_PREFIXES = ("-- ", "--\t", "--\n", "#")


def load_sql_file(path: str) -> str:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Archivo no encontrado: {path}")
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def split_statements(raw_sql: str) -> List[str]:
    """Divide por ';' respetando que las líneas de comentario se ignoren.
    Método simple suficiente para dumps estándar de phpMyAdmin sin delimitadores personalizados.
    """
    # Eliminar comentarios de bloque simples /* ... */ conservando saltos
    cleaned = re.sub(r"/\*![^*]*\*/", "", raw_sql)
    cleaned = re.sub(r"/\*[^!][\s\S]*?\*/", "", cleaned)

    parts = []
    current = []
    for line in cleaned.splitlines():
        striped = line.strip()
        # Ignorar comentarios de línea
        if not striped or any(striped.startswith(p) for p in COMMENT_LINE_PREFIXES):
            continue
        current.append(line)
        # Fin de sentencia heurístico: línea termina con ';'
        if striped.endswith(';'):
            stmt = '\n'.join(current).strip()
            parts.append(stmt[:-1].strip())  # quitar ';'
            current = []
    # Cualquier resto
    if current:
        stmt = '\n'.join(current).strip()
        if stmt:
            parts.append(stmt.rstrip(';').strip())
    return parts


def categorize(statements: List[str]) -> Dict[str, List[str]]:
    buckets = {"insert": [], "create": [], "other": []}
    for s in statements:
        if INSERT_REGEX.match(s):
            buckets["insert"].append(s)
        elif CREATE_REGEX.match(s):
            buckets["create"].append(s)
        else:
            buckets["other"].append(s)
    return buckets


def table_has_rows(table: str) -> bool:
    try:
        result = db.session.execute(text(f"SELECT 1 FROM `{table}` LIMIT 1"))
        return result.first() is not None
    except Exception:
        return False


def execute_statements(stmts: List[str], echo: bool, continue_on_error: bool = True) -> Tuple[int, int]:
    ok = 0
    failed = 0
    for s in stmts:
        try:
            if echo:
                print(f"--> {s[:140]}{'...' if len(s) > 140 else ''}")
            db.session.execute(text(s))
            ok += 1
        except IntegrityError as ie:
            db.session.rollback()
            failed += 1
            print(f"[IntegrityError] {ie.orig} -> se omite y continúa")
            if not continue_on_error:
                break
        except SQLAlchemyError as se:
            db.session.rollback()
            failed += 1
            print(f"[SQLAlchemyError] {se} -> se omite")
            if not continue_on_error:
                break
    return ok, failed


def main():
    parser = argparse.ArgumentParser(description="Importar datos desde dump SQL")
    parser.add_argument('--file', required=True, help='Ruta al archivo .sql')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--full', action='store_true', help='Ejecutar todas las sentencias (CREATE, INSERT, etc.)')
    group.add_argument('--data-only', action='store_true', help='Solo ejecutar INSERT (default)')
    parser.add_argument('--force', action='store_true', help='Ignorar si tablas ya tienen datos')
    parser.add_argument('--echo', action='store_true', help='Mostrar cada sentencia ejecutada')
    parser.add_argument('--stop-on-error', action='store_true', help='Detener en el primer error')
    parser.add_argument('--config', default='development', help='Nombre de configuración Flask (development|production|testing)')
    args = parser.parse_args()

    app = create_app(args.config)
    with app.app_context():
        raw = load_sql_file(args.file)
        statements = split_statements(raw)
        buckets = categorize(statements)

        print("Resumen del archivo:")
        print(f"  CREATE: {len(buckets['create'])}")
        print(f"  INSERT: {len(buckets['insert'])}")
        print(f"  OTROS : {len(buckets['other'])}")
        # Muestras diagnósticas si no se detectan INSERT
        if len(buckets['insert']) == 0:
            print("[Diagnóstico] No se detectaron sentencias INSERT. Primeras 5 sentencias clasificadas como 'otros':")
            for sample in buckets['other'][:5]:
                first_line = sample.splitlines()[0].strip()
                print(f"   -> {first_line[:120]}")

        to_run: List[str] = []
        mode = 'insert'
        if args.full:
            mode = 'full'
            to_run.extend(buckets['create'])
            to_run.extend(buckets['insert'])
            to_run.extend(buckets['other'])
        else:
            # default: data-only
            to_run.extend(buckets['insert'])

        # Si es solo datos, verificar tablas con datos para evitar duplicados
        if mode == 'insert' and not args.force:
            filtered = []
            skipped_tables = set()
            for stmt in to_run:
                m = INSERT_REGEX.match(stmt)
                if not m:
                    continue
                table = m.group('table')
                if table_has_rows(table):
                    skipped_tables.add(table)
                else:
                    filtered.append(stmt)
            if skipped_tables:
                print("Tablas con datos existentes (saltadas, use --force para forzar inserción):")
                for t in sorted(skipped_tables):
                    print(f"  - {t}")
            to_run = filtered

        if not to_run:
            print("No hay sentencias a ejecutar con los criterios actuales.")
            return

        print(f"Ejecutando {len(to_run)} sentencias en modo {'FULL' if args.full else 'DATA-ONLY'}...")
        ok, failed = execute_statements(to_run, echo=args.echo, continue_on_error=not args.stop_on_error)

        # Commit final
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error en commit final: {e}")
            sys.exit(1)

        print("Resultado:")
        print(f"  OK     : {ok}")
        print(f"  Fallidas: {failed}")
        if failed == 0:
            print("Importación completada sin errores críticos.")
        else:
            print("Importación finalizada con algunas fallas (ver arriba).")


if __name__ == '__main__':
    main()
