from agno.run.agent import RunContentCompletedEvent, RunContentEvent, ToolCallStartedEvent, ToolCallCompletedEvent, \
    RunStartedEvent, RunCompletedEvent
from slack_bolt.async_app import AsyncApp, AsyncAck
from slack_sdk.web.async_chat_stream import AsyncChatStream
from slack_sdk.web.async_client import AsyncWebClient

from src.chatbot.service import run_request, forget_preference, recall_preferences
from src.database.service import fetch_email, store_email


def register_handlers(slack_app: AsyncApp):
    async def publish_app_home(client: AsyncWebClient, user_id: str):
        async def render_preferences() -> list[dict]:
            return header_preferences_header() + await render_preferences_content()

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

        async def render_preferences_content() -> list[dict]:
            preferences = await recall_preferences(user_id=user_id)
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

        async def render_settings() -> list[dict]:
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
                        "initial_value": await get_email(),
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

        async def get_email() -> str:
            database_email = fetch_email(user_id)
            if not database_email:
                user_email = (await slack_app.client.users_info(user=user_id))['user']['profile']['email']
                store_email(user_id, user_email)
                return user_email
            return database_email

        await client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": await render_preferences() + await render_settings()
            }
        )

    @slack_app.event("app_home_opened")
    async def slack_app_event_app_home_opened(ack: AsyncAck, client: AsyncWebClient, event: dict) -> None:
        await ack()
        if event.get("tab", None) != "home":
            return

        user_id = event["user"]
        print(f"[{user_id}] App home opened.")

        await publish_app_home(client, user_id)

    @slack_app.action("preference_deleted")
    async def slack_app_action_preference_deleted(ack: AsyncAck, client: AsyncWebClient, action: dict, body: dict) -> None:
        await ack()

        user_id = body["user"]["id"]
        preference_id = action["value"]
        print(f"[{user_id}] Receiving request for deletion of preference {preference_id}.")

        forget_preference(user_id=user_id, preference_id=preference_id)

        await publish_app_home(client, user_id)

    @slack_app.action("email_updated")
    async def app_action_email_updated(ack: AsyncAck, client: AsyncWebClient, action: dict, body: dict) -> None:
        await ack()

        user_id = body['user']['id']
        email = action['value']
        print(f"[{user_id}] Receiving update request for setting 'email': '{email}'")

        store_email(user_id, email)

        await publish_app_home(client, user_id)

    @slack_app.event("message")
    async def slack_app_event_message(ack: AsyncAck, client: AsyncWebClient, event: dict) -> None:
        async def start_stream() -> AsyncChatStream:
            return await client.chat_stream(
                channel=event["channel"],
                thread_ts=event["ts"],
                buffer_size=32, # For a nicer effect.
                unfurl_links=False
            )
        async def append_to_stream(message: str) -> None:
            await stream.append(
                markdown_text=message,
            )
        async def post_message(message: str) -> str:
            return (await client.chat_postMessage(
                markdown_text=message,
                channel=event["channel"],
                thread_ts=event["ts"],
                unfurl_links=False
            ))["ts"]
        async def update_message(ts: str, message: str) -> None:
            await client.chat_update(
                ts=ts,
                markdown_text=message,
                channel=event["channel"],
                thread_ts=event["ts"],
                unfurl_links=False
            )

        await ack()

        user_id = event["user"]
        session_id = event["thread_ts"].replace(".", "")
        print(f"[{user_id}-{session_id}] Received message.")

        stream = await start_stream()

        original_message_ts = ""
        async for partial in run_request(user_id=user_id, session_id=session_id, message=event["text"]):
            match partial:
                case RunContentEvent():
                    await append_to_stream(partial.content)
                case RunContentCompletedEvent():
                    await stream.stop()
                case ToolCallStartedEvent():
                    original_message_ts = await post_message(f":gear: `{partial.tool.tool_name}`")
                case ToolCallCompletedEvent():
                    await update_message(original_message_ts, f":white_check_mark: `{partial.tool.tool_name}`")
                case RunStartedEvent() | RunCompletedEvent():
                    pass
                case _:
                    print("Unhandled event:", partial)

        print(f"[{user_id}-{session_id}] Responded to message.")

