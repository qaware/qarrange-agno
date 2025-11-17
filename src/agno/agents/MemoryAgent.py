from textwrap import dedent

from agno.memory import MemoryManager
from agno.models.openai import OpenAIChat

from src.agno.agents import agentic_database

MEMORY_MANAGER_MODEL = "gpt-5.1-chat-latest"
MEMORY_MANAGER_CAPTURE_INSTRUCTIONS = dedent("""
    Memories should capture user preferences regarding their calendar and schedule, for instance:
    - Information about meetings that are generally unimportant to the user and may be overwritten by new events
    - Standard working hours of the users
    - Hours that are generally preferred or disfavoured for meetings
    - Upcoming absences
    - Aversions regarding other colleagues
""")
MEMORY_MANAGER_INSTRUCTIONS = dedent("""
    You MUST store the memories in the language of the user request.
""")

memory_agent = MemoryManager(
    model=OpenAIChat(id=MEMORY_MANAGER_MODEL),
    memory_capture_instructions=MEMORY_MANAGER_CAPTURE_INSTRUCTIONS,
    additional_instructions=MEMORY_MANAGER_INSTRUCTIONS,
    db=agentic_database,
)
