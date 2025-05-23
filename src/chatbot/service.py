from src.agno.agents import preference_memory
from src.agno.agents.SecretaryAgent import SecretaryAgent


def handle_request(user_id: str, session_id: str, message: str) -> str:
    return SecretaryAgent(user_id=user_id, session_id=session_id).run(message=f"{user_id}: {message}").content


def recall_preferences(user_id: str) -> dict[str, str]:
    memories = preference_memory.get_user_memories(user_id=user_id)
    return {memory.memory_id: memory.memory for memory in reversed(memories)}


def forget_preference(user_id: str, preference_id: str) -> None:
    preference_memory.delete_user_memory(preference_id, user_id=user_id)
