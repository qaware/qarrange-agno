from agno.db.sqlite import SqliteDb

from src.database import DB_FILE

agentic_database = SqliteDb(
    db_file=DB_FILE
)
