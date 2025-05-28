from datetime import datetime, timedelta

from agno.agent import Agent
from agno.exceptions import AgentRunException
from agno.models.openai import OpenAIChat

from src.agno.agents import agent_session_storage, preference_memory
from src.agno.agents.BrokerAgent import BrokerAgent
from src.database.service import fetch_email
from src.google.calendar import GoogleCalendar

AGENT_MODEL = "gpt-4.1"
AGENT_NAME = "Secretary Agent"
AGENT_DESCRIPTION = "Process user requests for the scheduling of meetings and memorize user preferences."
AGENT_INSTRUCTIONS = [
    "Process requests from the user to establish a new calendar event.",
    "The request must contain a meeting title.",
    "The request must contain some form of date. NO PRECISE DATE AND TIME ARE REQUIRED. VAGUE STATEMENTS LIKE 'anytime next week' OR 'tomorrow afternoon' ARE TOTALLY FINE!",
    "The request must contain a meeting duration.",
    "The request must contain the desired participants. They must be given in the format <@U...>. The requesting user is implicitly one of the participants.",
    "If any of the required information is missing, query it from the user.",
    "As soon as all required information is collected, summarize it and ask for confirmation.",
    "Once confirmed, initiate the scheduling of the meeting.",
    "If the scheduling succeeded, add the event to the participants' calendars and provide the event URL to the user.",
]


class SecretaryAgent(Agent):

    def __init__(
            self, *,
            user_id: str | None = None,
            session_id: str | None = None
    ) -> None:
        self._session_id_of_caller_context = session_id
        self.session_id = f"{self._session_id_of_caller_context}-{self.__class__.__name__}"
        self._calendar = GoogleCalendar(fetch_email(user_id))

        print(f"[{user_id}-{self.session_id}] Initializing.")

        super().__init__(
            model=OpenAIChat(id=AGENT_MODEL),
            name=AGENT_NAME,
            description=AGENT_DESCRIPTION,
            instructions=AGENT_INSTRUCTIONS,
            agent_id=self.__class__.__name__,
            user_id=user_id,
            session_id=self.session_id,
            session_name=self.session_id, # TODO: https://github.com/agno-agi/agno/issues/3328
            storage=agent_session_storage,
            memory=preference_memory,
            enable_agentic_memory=True,
            add_datetime_to_instructions=True,
            add_history_to_messages=True,
            num_history_responses=64,
            tools=[self._initiate_scheduling, self._create_event],
            show_tool_calls=True,
            debug_mode=True
        )

    def _initiate_scheduling(
            self,
            title: str,
            date: str,
            duration: str,
            participants: list[str],
    ) -> str:
        """
        Use this function to initiate the negotiation of a time slot that works for all participants based on their schedules and preferences.
        In case of success, the result will be an exact time slot. This function call does *not* add the event to calendars.

        Args:
            title (str): The meeting title
            date (str): The meeting date (can be vague, e.g. 'anytime next week' or 'tomorrow afternoon')
            duration (str): The meeting duration
            participants (list[str]): The list of meeting participants, each referenced in the form 'U...'

        Returns:
            str: The answer of the broker agent containing the negotiated time slot
        """

        print(f"[{self.user_id}-{self.session_id}] Initialize scheduling of event:")
        print(f"  Title: {title}")
        print(f"  Date: {date}")
        print(f"  Duration: {duration}")
        print(f"  Participants: {participants}")

        if self.user_id not in participants:
            participants.append(self.user_id)

        broker = BrokerAgent(
            user_id=self.user_id,
            session_id=self._session_id_of_caller_context,
            participants=participants
        )
        return broker.find_time_slot(title=title, date=date, duration=duration, participants=participants)

    def _create_event(
            self,
            title: str,
            start_datetime: str,
            duration_minutes: int,
            participants: list[str],
    ) -> str:
        """
        Use this function to create calendar events.

        Args:
            title (str): The meeting title
            start_datetime (str): The exact meeting date and time in format 'YYYY-MM-DDTHH:MM:SS'
            duration_minutes (int): The meeting duration in minutes
            participants (list[str]): The list of meeting participants, each referenced in the form 'U...'

        Returns:
            str: The web URL of the created event
        """

        if not self._calendar.is_correctly_configured():
            raise AgentRunException("Calendar not configured for user.")

        print(f"[{self.user_id}-{self.session_id}] Creating event.")

        return self._calendar.create_event(
            title=title,
            start_datetime=datetime.fromisoformat(start_datetime),
            end_datetime=datetime.fromisoformat(start_datetime) + timedelta(minutes=duration_minutes),
            participants_emails=[fetch_email(participant) for participant in participants]
        )
