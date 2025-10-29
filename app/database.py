import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

# --- Dynamic Database URL Configuration ---

# 1. Retrieve connection details from environment variables (set by Render's render.yaml)
DB_HOST = os.environ.get("DB_HOST")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")

# 2. Construct the DATABASE_URL dynamically
# The 'sslmode=require' is critical for Render's PostgreSQL connection
if all([DB_HOST, DB_NAME, DB_USER, DB_PASS]):
    # This URL connects to the Render-provisioned PostgreSQL database
    DATABASE_URL = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}?sslmode=require"
    )
else:
    # Fallback for local development or if environment variables are missing
    # You should set up a local database (e.g., SQLite) for testing here
    DATABASE_URL = "sqlite:///./local_db.db"


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

# Auto-create tables (This runs the first time the app connects to the DB)
Base.metadata.create_all(bind=engine)