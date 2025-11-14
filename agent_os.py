from agno.os import AgentOS

from src.agno.agents.BrokerAgent import BrokerAgent
from src.agno.agents.SecretaryAgent import SecretaryAgent
from src.agno.agents.UserAgent import UserAgent
from src.database.service import list_all_user_ids

agent_os = AgentOS(
    agents=[
        SecretaryAgent()
    ] + [
        UserAgent(participant_user_id=user_id) for user_id in list_all_user_ids()
    ],
    teams=[
        BrokerAgent(),
    ]
)

app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve("agent_os:app", reload=True)
