"""
Configuración centralizada del sistema de logging.
"""
import logging
import sys


def configure_logging(app):
    """Configura logging sin duplicación en producción bajo Gunicorn."""
    try:
        if ('gunicorn' in sys.modules) or os.getenv('GUNICORN_CMD_ARGS') or (os.getenv('SERVER_SOFTWARE') or '').lower().startswith('gunicorn'):
            g_error = logging.getLogger('gunicorn.error')
            root = logging.getLogger()
            if g_error and g_error.handlers:
                root.handlers = g_error.handlers
                root.setLevel(g_error.level)
                app.logger.handlers = g_error.handlers
                app.logger.setLevel(g_error.level)
                app.logger.propagate = False
                logging.getLogger('werkzeug').setLevel(logging.WARNING)
                logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
                app.logger.info("Logging integrado con Gunicorn.")
                return
    except Exception:
        pass
    # Fallback sin añadir handlers: confiar en entorno
    lvl = app.config.get('LOG_LEVEL', logging.INFO)
    logging.getLogger().setLevel(lvl)
    app.logger.handlers = []
    app.logger.setLevel(lvl)
    app.logger.propagate = True
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
