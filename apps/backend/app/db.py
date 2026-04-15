from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings
from app.models import Base


engine = create_engine(settings.DATABASE_URL,pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=engine)

def init_db():
    # Creates all tables defined in models (Base.metadata.create_all)
    Base.metadata.create_all(bind=engine)
def get_db():
    # Generator - gives db session, ensures it closes after use
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()