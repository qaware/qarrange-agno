from datetime import date
from textwrap import dedent

from agno.agent import Agent
from agno.exceptions import AgentRunException
from agno.models.openai import OpenAIChat

from src.agno.agents import agentic_database
from src.agno.agents.MemoryAgent import memory_agent
from src.database.service import fetch_email
from src.google.calendar import GoogleCalendar

AGENT_MODEL = "gpt-4.1-mini"
AGENT_NAME = "User Agent {}"
AGENT_ROLE = "Agent providing information about the calendar and scheduling preferences of user {}"
AGENT_INSTRUCTIONS = dedent("""
    You are an agent that will be inquired of by the Broker Agent about availability of the user you represent on specific days and times.
    You do NOT interact with the user, you interact with the Broker Agent as part of an agentic workflow.
    The Broker agent is NOT interested in details about the user's calender or preferences. It is only interested in:
    - Timeslots that are available and favored, no matter why.
    - Timeslots that are available but disfavored, no matter why.
    - Timeslots that are unavailable, no matter why.
    Provide the Broker Agent with this information as simple bullet points (NO JSON) and in a short, efficient manner.
    Take user preferences into account, such as typical working hours or the importance of certain meetings.
    OFFER and ENCOURAGE your user's events to be overwritten, IF THEIR PREFERENCES SAY SO (e.g. 'meetings of type X are unimportant and may be overwritten').
    ONLY offer events to be overwritten, IF the user's preferences suggest so. Otherwise, they are FIXED blockers.
    RESPECT THE STANDARD WORKING HOURS Monday to Friday from 9 AM to 12 PM and 1 PM to 5 PM, IF no preference says otherwise.
    12 PM to 13 PM is LUNCH TIME where NO MEETINGS ARE ALLOWED.
""")


class UserAgent(Agent):
    def __init__(
            self, *,
            participant_user_id: str,
            initiator_user_id: str | None = None,
            session_id: str | None = None
    ) -> None:
        self._conversation_session_id = session_id
        self._participant_user_id = participant_user_id
        self.agent_id = f"{self.__class__.__name__}-{self._participant_user_id}"
        self.session_id = f"{self._conversation_session_id}-{self.agent_id}"

        print(f"[{initiator_user_id}-{self.session_id}] Initializing.")

        self._calendar = GoogleCalendar(fetch_email(participant_user_id))

        super().__init__(
            id=self.agent_id,
            model=OpenAIChat(id=AGENT_MODEL),
            name=AGENT_NAME.format(self._participant_user_id),
            role=AGENT_ROLE.format(self._participant_user_id),
            instructions=AGENT_INSTRUCTIONS,
            user_id=initiator_user_id,
            session_id=self.session_id,
            additional_context=self.get_user_preferences(),
            db=agentic_database,
            add_datetime_to_context=True,
            add_history_to_context=True,
            num_history_messages=64,
            tools=[self.read_calendar],
        )

    def get_user_preferences(self) -> str:
        return "User Preferences:\n- " + "\n- ".join([
            memory.memory for memory in reversed(memory_agent.get_user_memories(self._participant_user_id))
        ])

    def read_calendar(
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
