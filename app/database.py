from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

# Hardcoded PostgreSQL URL (replace with your actual credentials)
DATABASE_URL = "postgresql+psycopg2://postres_user:tkUtjzIbGmH8TvQfHuWvDiXM9ziSScno@dpg-d3cckmqdbo4c73e2b2s0-a:5432/postres_9ym9"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

def create_tables():
    Base.metadata.create_all(bind=engine)

# Automatically create tables when this module is imported
create_tables()
