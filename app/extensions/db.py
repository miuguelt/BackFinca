from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import text
from contextlib import contextmanager
import logging

engine = None
SessionLocal = None
_initialized = False

logger = logging.getLogger(__name__)

def init_db_session_management(app, db):
    global engine, SessionLocal, _initialized
    if _initialized:
        return
    with app.app_context():
        engine = db.engine
        SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))
        @app.teardown_appcontext
        def remove_scoped_session(exception=None):
            try:
                if SessionLocal:
                    SessionLocal.remove()
            except Exception:
                pass
        try:
            pool = getattr(engine, "pool", None)
            pool_size = getattr(pool, "size", lambda: None)()
            logger.info(f"SQLAlchemy engine inicializado: dialect={engine.dialect.name}, pool_size={pool_size}")
        except Exception:
            logger.info("SQLAlchemy engine inicializado")
        _initialized = True

@contextmanager
def get_db():
    session = SessionLocal()
    try:
        yield session
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise
    finally:
        try:
            session.close()
        except Exception:
            pass
