import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SQLITE_PATH = os.path.join(BASE_DIR, '..', 'attendance.db')

engine = create_engine(f'sqlite:///{SQLITE_PATH}', connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Create all tables if they do not exist"""
    import backend.models as models  # noqa: F401
    Base.metadata.create_all(bind=engine)

