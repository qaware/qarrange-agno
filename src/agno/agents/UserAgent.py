from datetime import date

from agno.agent import Agent
from agno.exceptions import AgentRunException
from agno.models.openai import OpenAIChat

from src.agno.agents import preference_memory, agent_session_storage
from src.database.service import fetch_email
from src.google.calendar import GoogleCalendar

AGENT_MODEL = "gpt-4.1"
AGENT_NAME = "User Agent {}"
AGENT_ROLE = "Represent user {} to the Calendar Broker Agent."
AGENT_INSTRUCTIONS = [
    "The Calendar Broker Agent will inquire about the user's availability on specific days and times.",
    "You do NOT interact with the user, but with the Calendar Broker Agent.",
    "Negotiate based on existing events and blockers in the calendar of the user you represent.",
    "Take user preferences into account, such as typical working hours or the importance of certain meetings.",
    "Be cooperative and facilitate compromises.",
    "OFFER and ENCOURAGE your user's events to be overwritten, IF THEIR PREFERENCES SAY SO (e.g. 'meetings of type X are unimportant and may be overwritten').",
    "If the user's preference do not indicate the unimportance of existing meetings, do NOT offer it to be overwritten. They are fixed blockers in that case.",
    "RESPECT THE STANDARD WORKING HOURS Monday to Friday from 9 AM to 12 PM and 1 PM to 5 PM, IF no preference says otherwise.",
    "12 PM to 13 PM is LUNCH TIME where NO MEETINGS ARE ALLOWED.",
]


class UserAgent(Agent):
    def __init__(
            self, *,
            participant_user_id: str,
            initiator_user_id: str | None = None,
            session_id: str | None = None
    ) -> None:
        self._session_id_without_context = session_id
        self._participant_user_id = participant_user_id
        self._calendar = GoogleCalendar(fetch_email(participant_user_id))
        self.agent_id = f"{self.__class__.__name__}-{self._participant_user_id}"
        self.session_id = f"{self._session_id_without_context}-{self.agent_id}"

        print(f"[{initiator_user_id}-{self.session_id}] Initializing.")

        super().__init__(
            model=OpenAIChat(id=AGENT_MODEL),
            name=AGENT_NAME.format(self._participant_user_id),
            role=AGENT_ROLE.format(self._participant_user_id),
            instructions=AGENT_INSTRUCTIONS,
            agent_id=self.agent_id,
            user_id=initiator_user_id,
            session_id=self.session_id,
            session_name=self.session_id,
            context={"user_preferences": self._get_user_preferences},
            add_context=True,
            storage=agent_session_storage,
            add_datetime_to_instructions=True,
            add_history_to_messages=True,
            num_history_responses=64,
            tools=[self._read_calendar],
            show_tool_calls=True,
            debug_mode=True
        )

    def _get_user_preferences(self) -> list[str]:
        return [memory.memory for memory in reversed(preference_memory.get_user_memories(self._participant_user_id))]

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

        print(f"[{self.user_id}-{self.session_id}] Reading calendar at {lookup_date}.")

        events = self._calendar.fetch_blocker_events(date.fromisoformat(lookup_date))
        return [
            {
                "start": event['start']['dateTime'],
                "end": event['end']['dateTime'],
                "summary": event['summary']
            } for event in events
        ]
