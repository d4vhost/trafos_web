from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import time

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./incidencias.db")

# Crear engine con pool_pre_ping para reconexión automática
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db(max_retries=5, wait_seconds=3):
    """Inicializar BD con reintentos para esperar a PostgreSQL."""
    for attempt in range(max_retries):
        try:
            Base.metadata.create_all(bind=engine)
            print(f"✓ Base de datos conectada e inicializada")
            return
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⏳ Esperando a PostgreSQL (intento {attempt + 1}/{max_retries})...")
                time.sleep(wait_seconds)
            else:
                print(f"✗ No se pudo conectar a la base de datos: {e}")
                raise
