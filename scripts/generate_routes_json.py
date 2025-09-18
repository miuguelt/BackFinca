"""
Generar routes.json a partir de app.url_map.

Este script crea un archivo routes.json en la raíz del proyecto con las rutas
registradas en Flask/Flask-RESTX. Inicializa la app en modo desarrollo y
normaliza las rutas para quitar el prefijo del Blueprint (p. ej. /api/v1),
produciendo una estructura con basePath y una lista de rutas únicas.
Además, enriquece cada método con el summary, operationId, tags, description, parameters, responses y security provenientes de swagger.json si está disponible,
y normaliza parámetros tipo <int:id> -> {id} y remueve el trailing slash (excepto en la raíz).
También incluye una agrupación por tags en routesByTag para facilitar la navegación en el frontend.
"""
import json
import os
import sys
import re
from datetime import datetime, timezone

# Asegurar import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app

API_PREFIX = '/api/v1'


def rule_methods(rule):
    methods = set(rule.methods or [])
    # Filtrar métodos útiles
    methods = methods.intersection({'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'})
    return sorted(methods)


def strip_prefix(path: str, prefix: str) -> str:
    if path.startswith(prefix):
        trimmed = path[len(prefix):]
        return trimmed if trimmed else '/'
    return path


def flask_to_swagger_path(path: str) -> str:
    """Convierte parámetros de Flask (<int:id>, <path:filename>, <id>) a estilo Swagger {id}."""
    return re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", path)


def canonicalize_path(path: str) -> str:
    """Normaliza el path: remueve trailing slash (si no es '/'), y convierte params a {param}."""
    if path != '/' and path.endswith('/'):
        path = path[:-1]
    return flask_to_swagger_path(path)


def load_swagger(swagger_path: str):
    try:
        with open(swagger_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def _simplify_param(p: dict) -> dict:
    """Extrae los campos relevantes de un parámetro Swagger 2.0.
    Mantiene solo: name, in, required, type. Si no hay type y hay schema, usa 'object'.
    """
    if not isinstance(p, dict):
        return {}
    name = p.get('name')
    loc = p.get('in')
    if not name or not loc:
        return {}
    typ = p.get('type')
    if not typ:
        # Para parámetros de cuerpo u otros definidos por schema
        schema = p.get('schema')
        if isinstance(schema, dict):
            typ = schema.get('type') or 'object'
        else:
            typ = 'object'
    return {
        'name': name,
        'in': loc,
        'required': bool(p.get('required', False)),
        'type': typ,
    }


def _merge_parameters(path_params: list, op_params: list) -> list:
    """Combina parámetros de nivel path y nivel operación.
    Los de operación sobreescriben a los de path si coinciden (name+in).
    """
    merged = {}
    for src in (path_params or []):
        sp = _simplify_param(src)
        if sp:
            merged[(sp['name'], sp['in'])] = sp
    for src in (op_params or []):
        sp = _simplify_param(src)
        if sp:
            merged[(sp['name'], sp['in'])] = sp
    # Retornar lista ordenada estable por clave (in, name) para consistencia
    return [merged[k] for k in sorted(merged.keys(), key=lambda x: (x[1], x[0]))]


def _simplify_responses(responses: dict) -> dict:
    """Convierte responses de Swagger 2.0 a {code: {description}} limitando a descripciones.
    """
    if not isinstance(responses, dict):
        return {}
    out = {}
    for code, info in responses.items():
        if not isinstance(info, dict):
            continue
        desc = info.get('description')
        if desc:
            out[str(code)] = { 'description': desc }
    return out


def build_meta_index(swagger: dict):
    """Construye un índice {(path, METHOD): {summary?, operationId?, tags?, description?, parameters?, responses?, security?}} desde swagger.json.
    Se normaliza el path para que coincida con el generado desde Flask (sin trailing slash y con {param}).
    """
    index = {}
    if not swagger or 'paths' not in swagger:
        return index
    for spath, ops in swagger.get('paths', {}).items():
        if not isinstance(ops, dict):
            continue
        cpath = canonicalize_path(spath)
        # Parámetros definidos a nivel de path
        path_level_params = ops.get('parameters') if isinstance(ops.get('parameters'), list) else []
        for method, meta in ops.items():
            # Ignorar la clave especial 'parameters' a nivel de path
            if method.lower() == 'parameters':
                continue
            if not isinstance(meta, dict):
                continue
            entry = {}
            summary = meta.get('summary')
            if summary:
                entry['summary'] = summary
            operation_id = meta.get('operationId')
            if operation_id:
                entry['operationId'] = operation_id
            tags = meta.get('tags')
            if isinstance(tags, list) and tags:
                entry['tags'] = tags
            description = meta.get('description')
            if description:
                entry['description'] = description
            # Combinar parámetros de path + operación
            op_params = meta.get('parameters') if isinstance(meta.get('parameters'), list) else []
            combined_params = _merge_parameters(path_level_params, op_params)
            if combined_params:
                entry['parameters'] = combined_params
            # Responses
            resp = _simplify_responses(meta.get('responses'))
            if resp:
                entry['responses'] = resp
            # Security (lista de esquemas usados, p. ej. ["Bearer", "Cookie"]) 
            sec = meta.get('security')
            if isinstance(sec, list) and sec:
                names = []
                for req in sec:
                    if isinstance(req, dict):
                        for k in req.keys():
                            if k not in names:
                                names.append(k)
                if names:
                    entry['security'] = names
            if entry:
                index[(cpath, method.upper())] = entry
    return index


def main():
    # Crear app en modo desarrollo (usa misma config que el servidor local)
    app = create_app(config_name='development')

    # Cargar metadatos desde swagger.json si está disponible
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    swagger = load_swagger(os.path.join(project_root, 'swagger.json'))
    meta_index = build_meta_index(swagger)

    routes = {}
    with app.app_context():
        for rule in app.url_map.iter_rules():
            # Ignorar rutas estáticas
            if rule.endpoint == 'static' or str(rule.rule).startswith('/static'):
                continue

            methods = rule_methods(rule)
            if not methods:
                continue

            raw_path = str(rule.rule)
            path = strip_prefix(raw_path, API_PREFIX)
            path = canonicalize_path(path)

            # Acumular métodos por path normalizado
            routes.setdefault(path, set()).update(methods)

    # Convertir a estructura final y ordenar
    items = []
    for path in sorted(routes.keys()):
        method_names = sorted(routes[path])
        methods = []
        for m in method_names:
            entry = {'method': m}
            meta = meta_index.get((path, m))
            if meta:
                entry.update(meta)
            methods.append(entry)
        items.append({'path': path, 'methods': methods})

    # Construir agrupación por tags para facilitar uso en frontend
    tag_routes = {}
    for item in items:
        p = item['path']
        for m in item['methods']:
            tags = m.get('tags') or []
            if not tags:
                tags = ['untagged']
            for t in tags:
                tag_routes.setdefault(t, {}).setdefault(p, []).append({
                    'method': m['method'],
                    **({'summary': m['summary']} if 'summary' in m else {}),
                    **({'operationId': m['operationId']} if 'operationId' in m else {}),
                })

    # Normalizar estructura: convertir dicts internos a listas ordenadas
    routes_by_tag = {}
    for t in sorted(tag_routes.keys()):
        path_map = tag_routes[t]
        grouped = []
        for pth in sorted(path_map.keys()):
            methods = sorted(path_map[pth], key=lambda x: x['method'])
            grouped.append({'path': pth, 'methods': methods})
        routes_by_tag[t] = grouped

    out = {
        'basePath': API_PREFIX,
        'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'routes': items,
        'routesByTag': routes_by_tag,
    }

    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'routes.json'))
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"routes.json generado en: {out_path}")


if __name__ == '__main__':
    main()
