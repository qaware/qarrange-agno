import asyncio
import os

from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp

from src.slack.handlers import register_handlers

load_dotenv()

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]


async def main():
    slack_app = AsyncApp(token=SLACK_BOT_TOKEN)
    register_handlers(slack_app)
    slack_handler = AsyncSocketModeHandler(slack_app, app_token=SLACK_APP_TOKEN)
    await slack_handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())
