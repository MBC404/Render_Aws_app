from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

# Replace with your real PostgreSQL credentials including SSL
DATABASE_URL = "postgresql+psycopg2://postres_user:tkUtjzIbGmH8TvQfHuWvDiXM9ziSScno@dpg-d3cckmqdbo4c73e2b2s0-a:5432/postres_9ym9?sslmode=require"

# Engine with connection pooling
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# User table
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

# Auto-create tables
Base.metadata.create_all(bind=engine)
