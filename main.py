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
preferences_memory = Memory(
    model=OpenAIChat(id=MEMORY_MODEL),
    db=SqliteMemoryDb(table_name="user_preferences", db_file=DB_FILE),
)

USER_MODEL = "gpt-4.1-mini"
USER_NAME = "Calendar User Agent for {}"
USER_ROLE = "Represent user {} in negotiating calendar events."
USER_INSTRUCTIONS = [
    "Process event setup requests from the broker on behalf of the user.",
    "Negotiate based on existing events and blockers in the calendar of the user.",
    "Take preferences of the user into account, such as typical working hours or events that are not actual blockers.",
    "Be cooperative and facilitate compromises."
    "If the user's preferences indicate that an existing blocker is not that important, ALLOW IT TO BE OVERWRITTEN WITHOUT ASKING FOR FURTHER CONSENT."
    "Assume standard working hours from 9 AM to 12 PM and 1 PM to 5 PM.",
    "12 PM to 13 PM is lunch time where no meetings are allowed.",
]

BROKER_MODEL = "o4-mini"
BROKER_NAME = "Calendar Broker Agent"
BROKER_DESCRIPTION = "Coordinate the negotiation of a new calendar event among multiple user agents."
BROKER_INSTRUCTIONS = [
    "Receive requests to find a time slot for a meeting with specified participants.",
    "Query each participant's calendar agent for available time slots.",
    "Negotiate back and forth until consensus on a time slot is achieved.",
    "Reiterate the inquiries with the agents in case of conflicts, asking for suggested alternatives and compromises.",
    "IN CASE OF CONFLICTS, DO NOT IMMEDIATELY RESPOND TO THE CALLER! Instead, continue to negotiate with the calendar user agents.",
    "Your goal is to provide the caller with a result, not with choices."
]

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
]

class UserAgent(Agent):
    def __init__(self, session_id: str, user_id: str):

        user_preferences = "None" # TODO: inject actual memories

        if user_id == "U08FBNWBJKU":
            additional_context = textwrap.dedent(f'''
                Existing calendar blockers of user:
                - Sales meeting next Friday 9 AM to 12 PM
                Preferences of user:
                {textwrap.dedent(user_preferences)}
            ''').strip()
        else:
            additional_context = textwrap.dedent(f'''
                Existing calendar blockers of user:
                - Marketing meeting next Friday 13 PM to 17 PM
                Preferences of user:
                {textwrap.dedent(user_preferences)}
            ''').strip()

        super().__init__(
            model=OpenAIChat(id=USER_MODEL),
            # session_id=session_id,
            name=USER_NAME.format(user_id),
            role=USER_ROLE.format(user_id),
            instructions=USER_INSTRUCTIONS,
            additional_context=additional_context,
            add_datetime_to_instructions=True,
        )

class BrokerAgent(Team):

    def __init__(self, *, session_id: str, participants: list[str]):
        members = [UserAgent(session_id, participant) for participant in participants]
        super().__init__(
            model=OpenAIChat(id=BROKER_MODEL),
            mode="coordinate",
            # session_id=session_id,
            name=BROKER_NAME,
            description=BROKER_DESCRIPTION,
            instructions=BROKER_INSTRUCTIONS,
            add_datetime_to_instructions=True,
            members=members
        )

    def find_time_slot(self, *, title: str, date: str, duration: str, participants: list[str]):
        message = textwrap.dedent(f"""
        Try to schedule a meeting based on the following data:
        - Title: {title}
        - Date: {date}
        - Duration: {duration}
        - Participants: {", ".join(participants)}
        """).strip()
        return super().run(message).content

class SecretaryAgent(Agent):

    def __init__(self, user_id: str, session_id: str = None):
        storage = SqliteAgentStorage(
            table_name="agent_sessions",
            db_file=DB_FILE,
        )
        super().__init__(
            model=OpenAIChat(id=SECRETARY_MODEL),
            user_id=user_id,
            session_id=session_id,
            name=SECRETARY_NAME.format(user_id),
            role=SECRETARY_ROLE.format(user_id),
            instructions=SECRETARY_INSTRUCTIONS,
            storage=storage,
            memory=preferences_memory,
            enable_agentic_memory=True,
            add_datetime_to_instructions=True,
            add_history_to_messages=True,
            num_history_responses=64,
            tools=[self.__find_time_slot, self.__schedule_event],
        )

    def __find_time_slot(
            self,
            title: str,
            date: str,
            duration: str,
            participants: list[str],
    ) -> str:
        """
        Use this function to find a date and time that works for all participants based on their schedules and preferences.

        Args:
            title (str): The meeting title
            date x(str): The desired meeting date, possibly very vaguely
            duration (str): The meeting duration
            participants (list[str]): The list of meeting participants, each referenced in the form 'U...'
        """

        print("__find_time_slot:")
        print(title)
        print(date)
        print(duration)
        print(participants)

        if self.user_id not in participants:
            participants.append(self.user_id)

        broker = BrokerAgent(session_id=self.session_id, participants=participants)
        broker_answer = broker.find_time_slot(title=title, date=date, duration=duration, participants=participants)
        return broker_answer

    @staticmethod
    def __schedule_event(
            title: str,
            date: str,
            duration: str,
            participants: list[str],
    ) -> str:
        """
        Use this function to schedule an event, i.e. add it to the participants calendars.

        Args:
            title (str): The meeting title
            date x(str): The exact meeting date
            duration (str): The meeting duration
            participants (list[str]): The list of meeting participants, each referenced in the form 'U...'
        """

        # TODO: Actual implementation

        print("__schedule_event:")
        print(title)
        print(date)
        print(duration)
        print(participants)

        return "Success!"

def publish_app_home(client: WebClient, user_id: str):
    def build_header() -> list[dict]:
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

    def build_preference(preference_id: str, content: str) -> list[dict]:
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

    def build_no_preferences_info() -> list[dict]:
        return [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "_There are no preferences memorized yet._"
            }
        }]

    def build_preferences() -> list[dict]:
        memories = preferences_memory.get_user_memories(user_id=user_id)
        if len(memories) > 0:
            return [element for memory in reversed(memories) for element in build_preference(memory.memory_id, memory.memory)]
        else:
            return build_no_preferences_info()

    client.views_publish(
        user_id=user_id,
        view={
            "type": "home",
            "blocks": build_header() + build_preferences()
        }
    )

@slack_app.event("app_home_opened")
def app_event_app_home_opened(ack: Ack, client: WebClient, event: dict):
    ack()
    if event["tab"] != "home":
        return

    user_id = event["user"]
    print(f"User {user_id} opened the app home.")

    publish_app_home(client, user_id)

def sanitize_slack_message(message: str):
    return message.replace("**", "*")

@slack_app.action("delete_preference")
def handle_some_action(ack: Ack, client: WebClient, action: dict, body: dict):
    ack()

    user_id = body["user"]["id"]
    preference_id = action["value"]
    print(f"User {user_id} requested to delete preference {preference_id}.")

    preferences_memory.delete_user_memory(preference_id, user_id=user_id)

    publish_app_home(client, user_id)

@slack_app.event("message")
def app_event_message_im(client: WebClient, event: dict):
    print(f"User {event['user']} sent a private message.")

    secretary = SecretaryAgent(user_id=event["user"], session_id=event["thread_ts"])
    response = secretary.run(message=event["text"])
    client.chat_postMessage(
        text=sanitize_slack_message(response.content),
        channel=event["channel"],
        thread_ts=event["ts"]
    )


slack_handler.start()

# TODO: Correct session handling.
# TODO: Make use of Workflows.