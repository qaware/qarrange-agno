from textwrap import dedent

from agno.models.openai import OpenAIChat
from agno.team import Team

from src.agno.agents import agentic_database
from src.agno.agents.UserAgent import UserAgent

AGENT_MODEL = "gpt-5.1"
AGENT_NAME = "Broker Agent"
AGENT_DESCRIPTION = "Agent responsible for the negotiation of date and time for a meeting with multiple participants, represented by their respective User Agents."
AGENT_INSTRUCTIONS = dedent("""
    You are an agent that will be tasked with finding a suitable date and time for a meeting with specified participants.
    You will be tasked by a conversation partner called 'user', not to be confused with the User Agents (your team members).
    Interview each participant's availability from their respective User Agent.
    You are NOT interested in details about the user's calender or preferences. You are ONLY interested in:
        - Timeslots that are available and favored.
        - Timeslots that are available but disfavored.
        - Timeslots that are unavailable.
    Negotiate back and forth until consensus on a date and time is reached.
    Reiterate the inquiries with the agents in case of conflicts, asking for suggested alternatives and compromises.
    In case of conflicts, do NOT immediately respond to the caller! Instead, continue to negotiate with the User Agents.
    If a User Agent indicates that some of their user's existing blockers may be overwritten, MAKE USE OF THIS OFFER, WITHOUT checking back.
    Once you have achieved consensus, IMMEDIATELY report back to the caller. DO NOT inform the User Agents about the outcome.
    Your goal is to provide the caller with a final result (a definite date and time), not with choices. MAKE A DECISION!
    Important information about the User Agents you can communicate with:
        - The User Agents have read access to the calendar and the personal scheduling preferences of the desired meeting participants.
        - The User Agents CANNOT prompt the user or make final decisions, they can only provide the latest information about the calendars and personal scheduling preferences.
        - The User Agents CANNOT create calendar events. This will be done by the entity that is calling YOU.
        - The User Agents DO NOT care about the final outcome of the negotiation. They are just your source of information.
""")


class BrokerAgent(Team):

    def __init__(
            self, *,
            user_id: str | None = None,
            session_ts: str | None = None,
            participants: list[str] | None = None
    ) -> None:
        if participants is None:
            participants = []

        self.id = self.__class__.__name__
        self.user_id = user_id
        self.session_ts = session_ts
        self.session_id = f"{session_ts}-{self.id}"
        members = [
            UserAgent(
                participant_user_id=participant,
                user_id=user_id,
                session_ts=session_ts
            )
            for participant in participants
        ]

        print(f"[{self.logging_prefix}] Initializing.")

        super().__init__(
            id=self.id,
            model=OpenAIChat(id=AGENT_MODEL),
            name=AGENT_NAME,
            description=AGENT_DESCRIPTION,
            instructions=AGENT_INSTRUCTIONS,
            user_id=self.user_id,
            session_id=self.session_id,
            members=members,
            db=agentic_database,
            add_datetime_to_context=True,
            add_history_to_context=False,
            add_member_tools_to_context=False,
        )

    @property
    def logging_prefix(self) -> str:
        return f"{self.user_id}-{self.session_id}"

    async def find_time_slot(self, *, title: str, date: str, duration: str, participants: list[str]) -> str:
        print(f"[{self.logging_prefix}] Negotiating.")
        message = "Negotiate a time slot for the following meeting:\n"
        message += f"- Title: {title}\n"
        message += f"- Date: {date}\n"
        message += f"- Duration: {duration}\n"
        message += f"- Participants: {', '.join(participants)}"
        return (await super().arun(message)).content
