from agno.models.openai import OpenAIChat
from agno.team import Team

from src.agno.agents import session_storage_teams
from src.agno.agents.UserAgent import UserAgent

BROKER_MODEL = "o4-mini"
BROKER_NAME = "Calendar Broker Agent"
BROKER_DESCRIPTION = "Negotiate time slots for calendar event with user agents representing the participants."
BROKER_INSTRUCTIONS = [
    "Receive requests to find a time slot for a meeting with specified participants.",
    "Query each participant's Calendar User Agent for available time slots.",
    "Negotiate back and forth until consensus on a time slot is achieved.",
    "Reiterate the inquiries with the agents in case of conflicts, asking for suggested alternatives and compromises.",
    "IN CASE OF CONFLICTS, DO NOT IMMEDIATELY RESPOND TO THE CALLER! Instead, continue to negotiate with the Calendar User Agents.",
    "Once you have achieved consensus, immediately report back to the caller. No need to inform the Calendar User Agents about the outcome.",
    "Your goal is to provide the caller with a final result (a definite time slot), not with choices.",
]
BROKER_SUCCESS_CRITERIA = "Achieve consensus on a meeting date and time or, as a last resort, announce that no common time slot can be found."


class BrokerAgent(Team):

    def __init__(self, *, user_id: str, session_id: str, participants: list[str]):
        self.__session_id_without_context = session_id
        self.__session_id = f"{self.__session_id_without_context}/{self.__class__.__name__}"
        print(f"[{user_id}/{self.__session_id}] Initializing.")

        members = [UserAgent(user_id, self.__session_id_without_context, participant) for participant in participants]
        super().__init__(
            model=OpenAIChat(id=BROKER_MODEL),
            mode="coordinate",
            user_id=user_id,
            session_id=self.__session_id,
            name=BROKER_NAME,
            description=BROKER_DESCRIPTION,
            instructions=BROKER_INSTRUCTIONS,
            success_criteria=BROKER_SUCCESS_CRITERIA,
            storage=session_storage_teams,
            add_datetime_to_instructions=True,
            members=members
        )

    def find_time_slot(self, *, title: str, date: str, duration: str, participants: list[str]):
        print(f"[{self.user_id}/{self.session_id}] Negotiating.")
        message = "Negotiate a time slot for the following meeting:"
        message += f"- Title: {title}"
        message += f"- Date: {date}"
        message += f"- Duration: {duration}"
        message += f"- Participants: {', '.join(participants)}"
        return super().run(message).content
