import os
import textwrap

from agno.agent import Agent
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.agent.sqlite import SqliteAgentStorage
from agno.team import Team
from slack_bolt import App, Ack
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

slack_app = App(token=SLACK_BOT_TOKEN)
slack_handler = SocketModeHandler(slack_app, app_token=SLACK_APP_TOKEN)

DB_FILE = "database.db"

MEMORY_MODEL = "gpt-4.1-mini"

preference_memory = Memory(
    model=OpenAIChat(id=MEMORY_MODEL),
    db=SqliteMemoryDb(table_name="preference_memory", db_file=DB_FILE),
)
session_storage_agents = SqliteAgentStorage(
    table_name="session_storage_agents",
    db_file=DB_FILE,
    mode="agent"
)
session_storage_teams = SqliteAgentStorage(
    table_name="session_storage_teams",
    db_file=DB_FILE,
    mode="team"
)

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

class UserAgent(Agent):
    def __init__(self, user_id: str, session_id: str, participant: str):

        additional_context = "Existing calendar blockers of user:\n"

        # TODO: Actual calendar integration
        if participant == "U08FBNWBJKU": # MBR
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
        message = textwrap.dedent(f"""
        Negotiate a time slot for the following meeting:
        - Title: {title}
        - Date: {date}
        - Duration: {duration}
        - Participants: {", ".join(participants)}
        """).strip()
        return super().run(message).content

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

        broker = BrokerAgent(user_id=self.user_id, session_id=self.__session_id_without_context, participants=participants)
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

def publish_app_home(client: WebClient, user_id: str):
    def header() -> list[dict]:
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Personal Calendar Preferences",
                    "emoji": True
                }
            },
            {
                "type": "divider"
            }
        ]
    def preference(preference_id: str, content: str) -> list[dict]:
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"_{content}_"
                },
                "accessory": {
                    "type": "button",
                    "action_id": "delete_preference",
                    "value": preference_id,
                    "text": {
                        "type": "plain_text",
                        "text": "Delete"
                    },
                    "style": "danger",
                    "confirm": {
                        "title": {
                            "type": "plain_text",
                            "text": "Are you sure?"
                        },
                        "text": {
                            "type": "plain_text",
                            "text": f"This will permanently delete the following preference:\n\"{content}\""
                        },
                        "confirm": {
                            "type": "plain_text",
                            "text": "Delete"
                        },
                        "deny": {
                            "type": "plain_text",
                            "text": "Cancel"
                        }
                    }
                }
            },
            {
                "type": "divider"
            }
        ]
    def no_preferences_info() -> list[dict]:
        return [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "_There are no preferences memorized yet._"
            }
        }]
    def preferences() -> list[dict]:
        memories = preference_memory.get_user_memories(user_id=user_id)
        if memories:
            return [element for memory in reversed(memories) for element in preference(memory.memory_id, memory.memory)]
        else:
            return no_preferences_info()

    client.views_publish(
        user_id=user_id,
        view={
            "type": "home",
            "blocks": header() + preferences()
        }
    )

@slack_app.event("app_home_opened")
def app_event_app_home_opened(ack: Ack, client: WebClient, event: dict):
    ack()
    if event["tab"] != "home":
        return

    user_id = event["user"]
    print(f"[{user_id}] App home opened.")

    publish_app_home(client, user_id)

@slack_app.action("delete_preference")
def handle_some_action(ack: Ack, client: WebClient, action: dict, body: dict):
    ack()

    user_id = body["user"]["id"]
    preference_id = action["value"]
    print(f"[{user_id}] Receiving request for deletion of preference {preference_id}.")

    preference_memory.delete_user_memory(preference_id, user_id=user_id)

    publish_app_home(client, user_id)

@slack_app.event("message")
def app_event_message_im(ack: Ack, client: WebClient, event: dict):
    def sanitize_slack_message(message: str):
        return message.replace("**", "*")

    ack()

    user_id = event["user"]
    session_id = event["thread_ts"]
    print(f"[{user_id}/{session_id}] Receiving message.")

    secretary = SecretaryAgent(user_id=user_id, session_id=session_id)
    response = secretary.run(message=event["text"])

    print(f"[{user_id}/{session_id}] Responding to message.")
    client.chat_postMessage(
        text=sanitize_slack_message(response.content),
        channel=event["channel"],
        thread_ts=event["ts"]
    )

slack_handler.start()

# TODO: Make use of Workflows.