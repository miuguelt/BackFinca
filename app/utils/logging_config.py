"""
Configuración centralizada del sistema de logging.
"""
import logging
import sys


def configure_logging(app):
    """Configura el sistema de logging optimizado de la aplicación."""
    log_level = app.config.get('LOG_LEVEL', logging.INFO)
    
    # Formato mejorado de logging
    log_format = (
        '%(asctime)s - [%(levelname)s] - %(name)s - '
        '%(funcName)s:%(lineno)d - %(message)s'
    )
    
    # Configurar handlers
    handlers = []
    
    # Handler para consola con colores
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    handlers.append(console_handler)
    
    # Handler para archivo si está habilitado
    if app.config.get('LOG_FILE_ENABLED', False):
        log_file = app.config.get('LOG_FILE', 'app.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # Configurar logging root
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers,
        force=True  # Sobrescribir configuración existente
    )
    
    # Configurar loggers específicos
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    # Logger para la aplicación
    app_logger = logging.getLogger('app')
    app_logger.setLevel(log_level)
    
    app_logger.info("Sistema de logging configurado exitosamente")