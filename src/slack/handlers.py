from slack_bolt import App, Ack
from slack_sdk import WebClient

from src.chatbot.service import handle_request, forget_preference, recall_preferences
from src.database.service import fetch_email, store_email


def register_handlers(slack_app: App):
    def publish_app_home(client: WebClient, user_id: str):
        def render_preferences() -> list[dict]:
            return header_preferences_header() + render_preferences_content()

        def header_preferences_header() -> list[dict]:
            return [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":brain: Memorized Preferences",
                        "emoji": True
                    }
                },
                {
                    "type": "divider"
                }
            ]

        def render_preferences_content() -> list[dict]:
            preferences = recall_preferences(user_id=user_id)
            if preferences:
                return [
                    element
                    for preference_id, preference_content in preferences.items()
                    for element in render_preference(preference_id, preference_content)
                ]
            else:
                return render_no_preferences()

        def render_preference(preference_id: str, content: str) -> list[dict]:
            return [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"_{content}_"
                    },
                    "accessory": {
                        "type": "button",
                        "action_id": "preference_deleted",
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

        def render_no_preferences() -> list[dict]:
            return [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "_There are no preferences memorized yet._"
                }
            }]

        def render_settings() -> list[dict]:
            return [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":gear: Settings",
                        "emoji": True
                    }
                },
                {
                    "type": "input",
                    "dispatch_action": True,
                    "element": {
                        "type": "plain_text_input",
                        "multiline": False,
                        "action_id": "email_updated",
                        "initial_value": get_email(),
                        "dispatch_action_config": {
                            "trigger_actions_on": ["on_enter_pressed"]
                        }
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Email Address"
                    }
                }
            ]

        def get_email() -> str:
            database_email = fetch_email(user_id)
            if not database_email:
                user_email = slack_app.client.users_info(user=user_id)['user']['profile']['email']
                store_email(user_id, user_email)
                return user_email
            return database_email

        client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": render_preferences() + render_settings()
            }
        )

    @slack_app.event("app_home_opened")
    def slack_app_event_app_home_opened(ack: Ack, client: WebClient, event: dict) -> None:
        ack()
        if event["tab"] != "home":
            return

        user_id = event["user"]
        print(f"[{user_id}] App home opened.")

        publish_app_home(client, user_id)

    @slack_app.action("preference_deleted")
    def slack_app_action_preference_deleted(ack: Ack, client: WebClient, action: dict, body: dict) -> None:
        ack()

        user_id = body["user"]["id"]
        preference_id = action["value"]
        print(f"[{user_id}] Receiving request for deletion of preference {preference_id}.")

        forget_preference(user_id=user_id, preference_id=preference_id)

        publish_app_home(client, user_id)

    @slack_app.action("email_updated")
    def app_action_email_updated(ack: Ack, client: WebClient, action: dict, body: dict) -> None:
        ack()

        user_id = body['user']['id']
        email = action['value']
        print(f"[{user_id}] Receiving update request for setting 'email': '{email}'")

        store_email(user_id, email)

        publish_app_home(client, user_id)

    @slack_app.event("message")
    def slack_app_event_message(ack: Ack, client: WebClient, event: dict) -> None:
        def sanitize_slack_message(message: str):
            return message.replace("**", "*")

        ack()

        user_id = event["user"]
        session_id = event["thread_ts"]
        print(f"[{user_id}/{session_id}] Receiving message.")

        response = handle_request(user_id=user_id, session_id=session_id, message=event["text"])

        print(f"[{user_id}/{session_id}] Responding to message.")
        client.chat_postMessage(
            text=sanitize_slack_message(response),
            channel=event["channel"],
            thread_ts=event["ts"],
            unfurl_links=False
        )
