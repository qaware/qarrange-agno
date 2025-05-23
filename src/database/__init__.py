from sqlalchemy import create_engine, Column, String, Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DB_FILE = "database.db"
SETTINGS_TABLE = "settings"

Base = declarative_base()


class UserSettings(Base):
    __tablename__ = SETTINGS_TABLE
    user_id = Column(String, primary_key=True)
    email = Column(String)


engine: Engine = create_engine(f'sqlite:///{DB_FILE}')
session: Session = sessionmaker(bind=engine)()

# Create all tables
Base.metadata.create_all(bind=engine)
