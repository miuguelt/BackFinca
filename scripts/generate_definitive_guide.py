import json
from pathlib import Path

def get_schema_details(schema_ref, swagger_data):
    """Obtiene los detalles de un esquema a partir de su referencia."""
    if not schema_ref or not schema_ref.startswith('#/definitions/'):
        return {}
    schema_name = schema_ref.split('/')[-1]
    return swagger_data.get('definitions', {}).get(schema_name, {})

def generate_example_from_schema(schema, swagger_data):
    """Genera un ejemplo de JSON a partir de un esquema, de forma recursiva."""
    if not isinstance(schema, dict):
        return None

    if 'example' in schema:
        return schema['example']

    example = {}
    properties = schema.get('properties', {})
    if not properties:
        return example

    for prop_name, prop_details in properties.items():
        prop_type = prop_details.get('type')
        
        if 'example' in prop_details:
            example[prop_name] = prop_details['example']
            continue

        if prop_type == 'integer':
            example[prop_name] = 1
        elif prop_type == 'string':
            if 'format' in prop_details and prop_details['format'] == 'date-time':
                example[prop_name] = '2025-09-06T10:00:00Z'
            else:
                example[prop_name] = f'string_value_for_{prop_name}'
        elif prop_type == 'boolean':
            example[prop_name] = True
        elif prop_type == 'number':
            example[prop_name] = 123.45
        elif '$ref' in prop_details:
            ref_schema = get_schema_details(prop_details['$ref'], swagger_data)
            example[prop_name] = generate_example_from_schema(ref_schema, swagger_data)
        elif prop_type == 'array':
            items_schema = prop_details.get('items', {})
            if '$ref' in items_schema:
                ref_schema = get_schema_details(items_schema['$ref'], swagger_data)
                example[prop_name] = [generate_example_from_schema(ref_schema, swagger_data)]
            else:
                example[prop_name] = [{'example_item': 'value'}]
        else:
            example[prop_name] = 'unknown'
            
    return example

def generate_definitive_guide(swagger_file, output_file):
    """Genera una guía completa y detallada para el frontend."""
    try:
        with open(swagger_file, 'r', encoding='utf-8') as f:
            swagger_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error al leer o parsear el archivo swagger.json: {e}")
        return

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Guía Definitiva de la API para el Frontend\n\n")
        f.write("Esta guía contiene todas las rutas, parámetros, y ejemplos de peticiones y respuestas de la API.\n\n")

        paths = swagger_data.get('paths', {})
        
        routes_by_tag = {}
        for path, methods in paths.items():
            for method, details in methods.items():
                if not isinstance(details, dict):
                    continue
                
                tag = details.get('tags', ['default'])[0]
                if tag not in routes_by_tag:
                    routes_by_tag[tag] = []
                
                # --- Parámetros ---
                parameters_info = {
                    'path': [],
                    'query': [],
                    'body': None
                }
                for param in details.get('parameters', []):
                    param_in = param.get('in')
                    param_details = {
                        'name': param.get('name'),
                        'description': param.get('description', 'N/A'),
                        'required': param.get('required', False),
                        'type': param.get('type', 'object')
                    }
                    if param_in == 'body':
                        schema_ref = param.get('schema', {}).get('$ref')
                        if schema_ref:
                            schema = get_schema_details(schema_ref, swagger_data)
                            param_details['schema'] = schema
                            param_details['example'] = generate_example_from_schema(schema, swagger_data)
                        parameters_info['body'] = param_details
                    elif param_in in ['path', 'query']:
                        parameters_info[param_in].append(param_details)

                # --- Respuestas ---
                responses_info = []
                for code, resp_details in details.get('responses', {}).items():
                    response = {
                        'code': code,
                        'description': resp_details.get('description', 'N/A'),
                        'example': None
                    }
                    schema_ref = resp_details.get('schema', {}).get('$ref')
                    if schema_ref:
                        schema = get_schema_details(schema_ref, swagger_data)
                        response['example'] = generate_example_from_schema(schema, swagger_data)
                    responses_info.append(response)

                routes_by_tag[tag].append({
                    'path': path,
                    'method': method.upper(),
                    'summary': details.get('summary', 'N/A'),
                    'description': details.get('description', ''),
                    'parameters': parameters_info,
                    'responses': sorted(responses_info, key=lambda x: x['code'])
                })

        # --- Escribir el archivo Markdown ---
        for tag in sorted(routes_by_tag.keys()):
            f.write(f"## {tag.replace('-', ' ').title()}\n\n")
            for route in sorted(routes_by_tag[tag], key=lambda x: x['path']):
                f.write(f"### `{route['method']}` {route['path']}\n\n")
                f.write(f"**{route['summary']}**\n\n")
                if route['description']:
                    f.write(f"{route['description'].strip()}\n\n")
                
                # Parámetros
                has_params = any(route['parameters'].values())
                if has_params:
                    f.write("#### Parámetros\n\n")
                    for param_type in ['path', 'query']:
                        if route['parameters'][param_type]:
                            f.write(f"**Parámetros de `{param_type}`:**\n\n")
                            for p in route['parameters'][param_type]:
                                f.write(f"- `{p['name']}` ({p['type']}, {'requerido' if p['required'] else 'opcional'}): {p['description']}\n")
                            f.write("\n")
                
                # Petición (Body)
                if route['parameters']['body']:
                    body_info = route['parameters']['body']
                    f.write("#### Petición (Body)\n\n")
                    if body_info.get('example'):
                        f.write("**Ejemplo de Petición:**\n")
                        f.write("```json\n")
                        f.write(json.dumps(body_info['example'], indent=2, ensure_ascii=False))
                        f.write("\n```\n\n")

                # Respuestas
                if route['responses']:
                    f.write("#### Posibles Respuestas\n\n")
                    for resp in route['responses']:
                        f.write(f"**`{resp['code']}`**: {resp['description']}\n")
                        if resp['example']:
                            f.write("```json\n")
                            f.write(json.dumps(resp['example'], indent=2, ensure_ascii=False))
                            f.write("\n```\n")
                        f.write("\n")

                f.write("---\n\n")

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    swagger_path = root / 'swagger.json'
    output_path = root / 'API_GUIDE_FOR_FRONTEND.md'
    generate_definitive_guide(swagger_path, output_path)
    print(f"Guía definitiva generada en: {output_path}")
