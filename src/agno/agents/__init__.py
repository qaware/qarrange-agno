from agno.memory.v2 import Memory
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.models.openai import OpenAIChat
from agno.storage.agent.sqlite import SqliteAgentStorage

DB_FILE = "database.db"

MEMORY_MODEL = "gpt-4.1-mini"

preference_memory = Memory(
    model=OpenAIChat(id=MEMORY_MODEL),
    db=SqliteMemoryDb(table_name="preference_memory", db_file=DB_FILE),
)
session_storage_agents = SqliteAgentStorage(
    table_name="session_storage_agents",
    db_file=DB_FILE,
    mode="agent"
)
session_storage_teams = SqliteAgentStorage(
    table_name="session_storage_teams",
    db_file=DB_FILE,
    mode="team"
)
