from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ENGINE = create_engine("sqlite:///futures.db", future=True, echo=False)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)
