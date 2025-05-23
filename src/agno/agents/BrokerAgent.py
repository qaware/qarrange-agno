from agno.models.openai import OpenAIChat
from agno.team import Team

from src.agno.agents import team_sessions_storage
from src.agno.agents.UserAgent import UserAgent

AGENT_MODEL = "o4-mini"
AGENT_NAME = "Broker Agent"
AGENT_DESCRIPTION = "Negotiate time slots for calendar event with user agents representing the participants."
AGENT_INSTRUCTIONS = [
    "Receive requests to find a time slot for a meeting with specified participants.",
    "Query each participant's Calendar User Agent for available time slots.",
    "Negotiate back and forth until consensus on a time slot is achieved.",
    "Reiterate the inquiries with the agents in case of conflicts, asking for suggested alternatives and compromises.",
    "IN CASE OF CONFLICTS, DO NOT IMMEDIATELY RESPOND TO THE CALLER! Instead, continue to negotiate with the Calendar User Agents.",
    "If Calendar User Agents indicate that some of their user's existing blockers may be overwritten, MAKE USE OF THIS OFFER, without checking back.",
    "Once you have achieved consensus, immediately report back to the caller. No need to inform the Calendar User Agents about the outcome.",
    "Your goal is to provide the caller with a final result (a definite time slot), not with choices.",
]
AGENT_SUCCESS_CRITERIA = "A consensus on meeting date and time is reached, or it is definitively determined that no common time slot exists."


class BrokerAgent(Team):

    def __init__(
            self, *,
            user_id: str | None = None,
            session_id: str | None = None,
            participants: list[str] | None = None
    ) -> None:
        if participants is None:
            participants = []

        self._session_id_without_context = session_id
        self.session_id = f"{self._session_id_without_context}-{self.__class__.__name__}"

        print(f"[{user_id}-{self.session_id}] Initializing.")

        members = [
            UserAgent(participant_user_id=participant, initiator_user_id=user_id,
                      session_id=self._session_id_without_context)
            for participant in participants
        ]
        super().__init__(
            model=OpenAIChat(id=AGENT_MODEL),
            name=AGENT_NAME,
            description=AGENT_DESCRIPTION,
            instructions=AGENT_INSTRUCTIONS,
            success_criteria=AGENT_SUCCESS_CRITERIA,
            team_id=self.__class__.__name__,
            user_id=user_id,
            session_id=self.session_id,
            session_name=self.session_id,
            storage=team_sessions_storage,
            add_datetime_to_instructions=True,
            mode="coordinate",
            members=members,
            read_team_history=True, # effect unclear
            enable_team_history=True, # effect unclear
            num_history_runs=64, # effect unclear
            add_member_tools_to_system_message=False
        )

    def find_time_slot(self, *, title: str, date: str, duration: str, participants: list[str]) -> str:
        print(f"[{self.user_id}-{self.session_id}] Negotiating.")
        message = "Negotiate a time slot for the following meeting:"
        message += f"- Title: {title}"
        message += f"- Date: {date}"
        message += f"- Duration: {duration}"
        message += f"- Participants: {', '.join(participants)}"
        return super().run(message).content
