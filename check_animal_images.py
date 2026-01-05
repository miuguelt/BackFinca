import os
import sys

# Agregar el directorio actual al path para poder importar los módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Verificar las imágenes directamente sin necesidad de la base de datos
print("Verificando imágenes del animal 52 en el sistema de archivos:")

# Directorio donde deberían estar las imágenes
directorio_imagenes = os.path.join('static', 'uploads', 'animals', '52')

if os.path.exists(directorio_imagenes):
    print(f"✓ Directorio encontrado: {directorio_imagenes}")
    archivos = os.listdir(directorio_imagenes)
    print(f"Archivos encontrados: {len(archivos)}")
    
    for archivo in archivos:
        ruta_completa = os.path.join(directorio_imagenes, archivo)
        print(f"  - {archivo}")
        print(f"    Ruta completa: {ruta_completa}")
        print(f"    Tamaño: {os.path.getsize(ruta_completa)} bytes")
        
        # Generar URL para frontend
        # Usar la configuración de BACKEND_URL del .env
        backend_url = "https://finca.enlinea.sbs"  # URL de producción según config.py
        url_publica = f"{backend_url}/static/uploads/animals/52/{archivo}"
        print(f"    URL pública: {url_publica}")
        print("-" * 50)
else:
    print(f"✗ Directorio no encontrado: {directorio_imagenes}")

# Verificar también si existe el directorio static/uploads en general
directorio_base = os.path.join('static', 'uploads')
if os.path.exists(directorio_base):
    print(f"✓ Directorio base encontrado: {directorio_base}")
    animales_dir = os.path.join(directorio_base, 'animals')
    if os.path.exists(animales_dir):
        print(f"✓ Directorio de animales encontrado: {animales_dir}")
        animales = os.listdir(animales_dir)
        print(f"Animales con directorios: {animales}")
    else:
        print(f"✗ Directorio de animales no encontrado: {animales_dir}")
else:
    print(f"✗ Directorio base no encontrado: {directorio_base}")