from agno.app.playground.app import Playground
from agno.app.playground.serve import serve_playground_app

from src.agno.agents.BrokerAgent import BrokerAgent
from src.agno.agents.SecretaryAgent import SecretaryAgent
from src.agno.agents.UserAgent import UserAgent
from src.database.service import list_all_user_ids

app = Playground(
    agents=[
        SecretaryAgent()
    ] + [
        UserAgent(participant_user_id=user_id) for user_id in list_all_user_ids()
    ],
    teams=[
        BrokerAgent(),
    ]
).get_app()

if __name__ == "__main__":
    serve_playground_app("playground:app", reload=True)
