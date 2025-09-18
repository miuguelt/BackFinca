import json
from pathlib import Path

def get_schema_details(schema_ref, swagger_data):
    """Obtiene los detalles de un esquema a partir de su referencia."""
    schema_name = schema_ref.split('/')[-1]
    return swagger_data.get('definitions', {}).get(schema_name, {})

def generate_example_from_schema(schema, swagger_data):
    """Genera un ejemplo de JSON a partir de un esquema."""
    if not schema:
        return None
    
    example = {}
    properties = schema.get('properties', {})
    for prop_name, prop_details in properties.items():
        if prop_details.get('type') == 'integer':
            example[prop_name] = 123
        elif prop_details.get('type') == 'string':
            if 'date' in prop_name:
                example[prop_name] = '2025-09-06T12:00:00Z'
            else:
                example[prop_name] = f'valor de {prop_name}'
        elif prop_details.get('type') == 'boolean':
            example[prop_name] = True
        elif prop_details.get('type') == 'number':
            example[prop_name] = 123.45
        elif '$ref' in prop_details:
            ref_schema = get_schema_details(prop_details['$ref'], swagger_data)
            example[prop_name] = generate_example_from_schema(ref_schema, swagger_data)
        elif prop_details.get('type') == 'array':
            items = prop_details.get('items', {})
            if '$ref' in items:
                ref_schema = get_schema_details(items['$ref'], swagger_data)
                example[prop_name] = [generate_example_from_schema(ref_schema, swagger_data)]
            else:
                example[prop_name] = []
        else:
            example[prop_name] = 'valor desconocido'
            
    return example

def generate_routes_guide(swagger_file, output_file):
    with open(swagger_file, 'r', encoding='utf-8') as f:
        swagger_data = json.load(f)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Guía de Rutas del Backend\n\n")
        f.write("Esta es una guía autogenerada de todas las rutas disponibles en el backend, con ejemplos de JSON.\n\n")

        paths = swagger_data.get('paths', {})
        
        # Agrupar rutas por su tag principal
        routes_by_tag = {}
        for path, methods in paths.items():
            for method, details in methods.items():
                # Ignorar 'parameters' que a veces aparece a nivel de path
                if method.lower() == 'parameters':
                    continue
                
                tag = details.get('tags', ['default'])[0]
                if tag not in routes_by_tag:
                    routes_by_tag[tag] = []
                
                # Extraer ejemplos de JSON
                input_example = None
                output_example = None

                # Ejemplo de entrada
                if 'parameters' in details:
                    for param in details['parameters']:
                        if param.get('in') == 'body':
                            schema_ref = param.get('schema', {}).get('$ref')
                            if schema_ref:
                                schema = get_schema_details(schema_ref, swagger_data)
                                input_example = generate_example_from_schema(schema, swagger_data)
                            break
                
                # Ejemplo de salida
                if 'responses' in details and '200' in details['responses']:
                    schema_ref = details['responses']['200'].get('schema', {}).get('$ref')
                    if schema_ref:
                        schema = get_schema_details(schema_ref, swagger_data)
                        output_example = generate_example_from_schema(schema, swagger_data)

                routes_by_tag[tag].append({
                    'path': path,
                    'method': method.upper(),
                    'summary': details.get('summary', 'No description available.'),
                    'description': details.get('description', ''),
                    'input_example': input_example,
                    'output_example': output_example
                })

        # Escribir las rutas agrupadas
        for tag in sorted(routes_by_tag.keys()):
            f.write(f"## {tag.replace('-', ' ').title()}\n\n")
            for route in routes_by_tag[tag]:
                f.write(f"### `{route['method']}` {route['path']}\n")
                f.write(f"**Descripción**: {route['summary']}\n")
                if route['description']:
                    # Limpiar la descripción para que sea más legible en markdown
                    clean_description = route['description'].replace('\n', ' ').strip()
                    f.write(f"{clean_description}\n")
                
                if route['input_example']:
                    f.write("\n**Ejemplo de Entrada (JSON):**\n")
                    f.write("```json\n")
                    f.write(json.dumps(route['input_example'], indent=2, ensure_ascii=False))
                    f.write("\n```\n")

                if route['output_example']:
                    f.write("\n**Ejemplo de Salida (JSON):**\n")
                    f.write("```json\n")
                    f.write(json.dumps(route['output_example'], indent=2, ensure_ascii=False))
                    f.write("\n```\n")

                f.write("\n---\n\n")

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    swagger_path = root / 'swagger.json'
    output_path = root / 'BACKEND_ROUTES.md'
    generate_routes_guide(swagger_path, output_path)
    print(f'Guía de rutas escrita en: {output_path}')
