from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from  .config import settings


"""
Database Architecture Explanation:

SQLAlchemy ORM (Object-Relational Mapping):
- Python Classes ↔ Database Tables
- Python Objects ↔ Database Rows
- Python Attributes ↔ Database Columns

Why ORM?
- Write Python, not SQL
- Type safety and autocompletion
- Automatic relationship handling
- Database vendor independence
"""
# engine
engine  = create_engine(
    settings.DATABASE_URl,
    echo = settings.DEBUG,
    pool_size=20,
    max_overflow=0
)
#local session in db
SessionLocal = sessionmaker(
    autocommit = False,
    autoflush=False,
    bind = engine
)

base = declarative_base()

def get_db(): #dependency func for route handlers
# FastAPI has a dependency injection system —
# it can "inject" shared or necessary objects into route handlers.
    """
      Dependency function for FastAPI routes

      What this does:
      1. Create new database session
      2. Yield it to the route function
      3. Automatically close session when done
      4. Handle errors gracefully
      """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""
runs up to yield → gives the db to your route,

waits until the request is done,

then resumes the function and calls db.close() safely.
"""
