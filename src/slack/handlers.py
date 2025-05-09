from slack_bolt import App, Ack
from slack_sdk import WebClient

from src.agno.agents import preference_memory
from src.agno.agents.SecretaryAgent import SecretaryAgent


def register_handlers(slack_app: App):
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
                return [element for memory in reversed(memories) for element in
                        preference(memory.memory_id, memory.memory)]
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
    def slack_app_event_app_home_opened(ack: Ack, client: WebClient, event: dict):
        ack()
        if event["tab"] != "home":
            return

        user_id = event["user"]
        print(f"[{user_id}] App home opened.")

        publish_app_home(client, user_id)

    @slack_app.action("delete_preference")
    def slack_app_action_delete_preference(ack: Ack, client: WebClient, action: dict, body: dict):
        ack()

        user_id = body["user"]["id"]
        preference_id = action["value"]
        print(f"[{user_id}] Receiving request for deletion of preference {preference_id}.")

        preference_memory.delete_user_memory(preference_id, user_id=user_id)

        publish_app_home(client, user_id)

    @slack_app.event("message")
    def slack_app_event_message(ack: Ack, client: WebClient, event: dict):
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
