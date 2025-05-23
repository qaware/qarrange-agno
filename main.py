import os

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from src.slack.handlers import register_handlers

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

if __name__ == "__main__":
    slack_app = App(token=SLACK_BOT_TOKEN)
    register_handlers(slack_app)
    slack_handler = SocketModeHandler(slack_app, app_token=SLACK_APP_TOKEN)
    slack_handler.start()
