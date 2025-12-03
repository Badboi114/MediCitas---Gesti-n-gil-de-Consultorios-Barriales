from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Creamos el archivo de base de datos (100% bajo tu control)
SQLALCHEMY_DATABASE_URL = "sqlite:///./medicitas.db"

# 2. Configuramos el motor (check_same_thread=False es necesario solo para SQLite)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. Creamos la sesión (la herramienta para guardar/leer datos)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Base para nuestros modelos
Base = declarative_base()
