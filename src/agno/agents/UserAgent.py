from datetime import date

from agno.agent import Agent
from agno.exceptions import AgentRunException
from agno.models.openai import OpenAIChat

from src.agno.agents import preference_memory, agent_session_storage
from src.database.service import fetch_email
from src.google.calendar import GoogleCalendar

USER_MODEL = "gpt-4.1"
USER_NAME = "Calendar User Agent for {}"
USER_ROLE = "Represent user {} in front of the Calendar Broker Agent."
USER_INSTRUCTIONS = [
    "The Calendar Broker Agent will ask you to provide available time slots for the user you represent.",
    "Remember that you do not interact with the user, but with the Calendar Broker Agent.",
    "Negotiate based on existing events and blockers in the calendar of your user.",
    "Take preferences of the user into account, such as typical working hours.",
    "Be cooperative and facilitate compromises.",
    "OFFER and ENCOURAGE your user's events to be overwritten if their preference allow it.",
    "Assume standard working hours from 9 AM to 12 PM and 1 PM to 5 PM, if no preference says otherwise.",
    "12 PM to 13 PM is lunch time where no meetings are allowed, if no preference says otherwise.",
]


class UserAgent(Agent):
    def __init__(self, user_id: str, session_id: str, participant: str) -> None:

        additional_context = "Preferences of user:\n"
        memories = preference_memory.get_user_memories(participant)
        for memory in memories:
            additional_context += f"- {memory.memory}\n"
        if not memories:
            additional_context += "None."

        self._session_id_without_context = session_id
        self._session_id = f"{self._session_id_without_context}/{self.__class__.__name__}/{participant}"
        self._calendar = GoogleCalendar(fetch_email(participant))

        print(f"[{user_id}/{self._session_id}] Initializing.")

        super().__init__(
            model=OpenAIChat(id=USER_MODEL),
            user_id=user_id,
            session_id=self._session_id,
            name=USER_NAME.format(participant),
            role=USER_ROLE.format(participant),
            instructions=USER_INSTRUCTIONS,
            additional_context=additional_context,
            storage=agent_session_storage,
            add_datetime_to_instructions=True,
            add_history_to_messages=True,
            num_history_responses=64,
            tools=[self._read_calendar]
        )

    def _read_calendar(
            self,
            lookup_date: str
    ) -> list[dict]:
        """
        Use this function the read the calendar of the user for a specific day.

        Args:
            lookup_date (str): The date in format 'YYYY-MM-DD'

        Returns:
            list[dict]: A list of blocker events on the specified day
        """
        if not self._calendar.is_correctly_configured():
            raise AgentRunException("Calendar not configured for user.")

        print(f"[{self.user_id}/{self.session_id}] Reading calendar at {lookup_date}.")

        events = self._calendar.fetch_blocker_events(date.fromisoformat(lookup_date))
        return [
            {
                "start": event['start']['dateTime'],
                "end": event['end']['dateTime'],
                "summary": event['summary']
            } for event in events
        ]
