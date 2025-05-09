from agno.agent import Agent
from agno.models.openai import OpenAIChat

from src.agno.agents import session_storage_agents, preference_memory
from src.agno.agents.BrokerAgent import BrokerAgent

SECRETARY_MODEL = "gpt-4.1"
SECRETARY_NAME = "Calendar Secretary Agent talking to {}"
SECRETARY_ROLE = "Process requests from {} for the scheduling of meetings."
SECRETARY_INSTRUCTIONS = [
    "Process requests from the user to establish a new calendar event.",
    "The request must contain a meeting title.",
    "The request must contain some form of date. NO PRECISE DATE AND TIME ARE REQUIRED. VAGUE STATEMENTS LIKE 'anytime next week' OR 'tomorrow afternoon' ARE TOTALLY FINE!",
    "The request must contain a meeting duration.",
    "The request must contain the desired participants. They must be given in the format <@U...>. The requesting user is implicitly one of the participants.",
    "If any of the required information is missing, query it from the user.",
    "As soon as all required information is collected, summarize it and ask for confirmation.",
    "Once confirmed, initiate the scheduling of the meeting.",
    "If the scheduling succeeded, add the event to the participants' calendars.",
]


class SecretaryAgent(Agent):

    def __init__(self, user_id: str, session_id: str = None):
        self.__session_id_without_context = session_id
        self.__session_id = f"{self.__session_id_without_context}/{self.__class__.__name__}"
        print(f"[{user_id}/{self.__session_id}] Initializing.")

        super().__init__(
            model=OpenAIChat(id=SECRETARY_MODEL),
            user_id=user_id,
            session_id=self.__session_id,
            name=SECRETARY_NAME.format(user_id),
            role=SECRETARY_ROLE.format(user_id),
            instructions=SECRETARY_INSTRUCTIONS,
            storage=session_storage_agents,
            memory=preference_memory,
            enable_agentic_memory=True,
            add_datetime_to_instructions=True,
            add_history_to_messages=True,
            num_history_responses=64,
            tools=[self.__initiate_scheduling, self.__create_event],
        )

    def __initiate_scheduling(
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
            date x(str): The desired meeting date, possibly very vaguely
            duration (str): The meeting duration
            participants (list[str]): The list of meeting participants, each referenced in the form 'U...'
        """

        print(f"[{self.user_id}/{self.session_id}] Scheduling event:")
        print(f"  Title: {title}")
        print(f"  Date: {date}")
        print(f"  Duration: {duration}")
        print(f"  Participants: {participants}")

        if self.user_id not in participants:
            participants.append(self.user_id)

        broker = BrokerAgent(user_id=self.user_id, session_id=self.__session_id_without_context,
                             participants=participants)
        broker_answer = broker.find_time_slot(title=title, date=date, duration=duration, participants=participants)
        return broker_answer

    def __create_event(
            self,
            title: str,
            date: str,
            duration: str,
            participants: list[str],
    ) -> str:
        """
        Use this function to create calendar events.

        Args:
            title (str): The meeting title
            date x(str): The exact meeting date
            duration (str): The meeting duration
            participants (list[str]): The list of meeting participants, each referenced in the form 'U...'
        """
        print(f"[{self.user_id}/{self.session_id}] Creating event:")
        print(f"  Title: {title}")
        print(f"  Date: {date}")
        print(f"  Duration: {duration}")
        print(f"  Participants: {participants}")

        # TODO: Actual implementation

        return "Success!"
