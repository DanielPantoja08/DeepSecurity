import os
from sqlmodel import create_engine, SQLModel, Session
from .models import * # Import models for table creation

# The database file is in the root by default
sqlite_file_name = "deepsecurity.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=False)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
