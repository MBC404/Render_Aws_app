from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_size=2,
    max_overflow=0,
    connect_args={"ssl": True}  # required for Render Postgres
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
