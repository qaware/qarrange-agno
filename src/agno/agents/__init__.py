from agno.memory.v2 import Memory
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.models.openai import OpenAIChat
from agno.storage.agent.sqlite import SqliteAgentStorage

from src.database import DB_FILE

MEMORY_MODEL = "gpt-4.1-mini"

preference_memory = Memory(
    model=OpenAIChat(id=MEMORY_MODEL),
    db=SqliteMemoryDb(table_name="preference_memory", db_file=DB_FILE),
)
agent_session_storage = SqliteAgentStorage(
    table_name="agent_session_storage",
    db_file=DB_FILE,
    mode="agent"
)
team_sessions_storage = SqliteAgentStorage(
    table_name="team_sessions_storage",
    db_file=DB_FILE,
    mode="team"
)
