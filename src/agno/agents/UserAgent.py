from agno.agent import Agent
from agno.models.openai import OpenAIChat

from src.agno.agents import preference_memory, session_storage_agents

USER_MODEL = "gpt-4.1-mini"
USER_NAME = "Calendar User Agent for {}"
USER_ROLE = "Represent user {} in front of the Calendar Broker Agent."
USER_INSTRUCTIONS = [
    "The Calendar Broker Agent will ask you to provide available time slots for the user you represent.",
    "Remember that you do not interact with the user, but with the Calendar Broker Agent.",
    "Negotiate based on existing events and blockers in the calendar of your user.",
    "Take preferences of the user into account, such as typical working hours.",
    "Be cooperative and facilitate compromises.",
    "Allow your user's events to be overwritten if their preference says they are unimportant.",
    "Assume standard working hours from 9 AM to 12 PM and 1 PM to 5 PM, if no preference says otherwise.",
    "12 PM to 13 PM is lunch time where no meetings are allowed, if no preference says otherwise.",
]


class UserAgent(Agent):
    def __init__(self, user_id: str, session_id: str, participant: str):

        additional_context = "Existing calendar blockers of user:\n"

        # TODO: Actual calendar integration
        if participant == "U08FBNWBJKU":  # MBR
            additional_context += "- Sales meeting next Friday 9 AM to 12 PM\n"
        else:
            additional_context += "- Marketing meeting next Friday 13 PM to 17 PM\n"

        additional_context += "Preferences of user:\n"
        memories = preference_memory.get_user_memories(participant)
        for memory in memories:
            additional_context += f"- {memory.memory}\n"
        if not memories:
            additional_context += "None."

        self.__session_id_without_context = session_id
        self.__session_id = f"{self.__session_id_without_context}/{self.__class__.__name__}/{participant}"
        print(f"[{user_id}/{self.__session_id}] Initializing.")

        super().__init__(
            model=OpenAIChat(id=USER_MODEL),
            user_id=user_id,
            session_id=self.__session_id,
            name=USER_NAME.format(participant),
            role=USER_ROLE.format(participant),
            instructions=USER_INSTRUCTIONS,
            additional_context=additional_context,
            storage=session_storage_agents,
            add_datetime_to_instructions=True,
            add_history_to_messages=True,
            num_history_responses=64,
        )
