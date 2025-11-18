from agno.os import AgentOS

from src.agno.agents.BrokerAgent import BrokerAgent
from src.agno.agents.SecretaryAgent import SecretaryAgent

agent_os = AgentOS(
    agents=[
        SecretaryAgent()
    ],
    teams=[
        BrokerAgent()
    ]
)

app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve("agent_os:app", reload=True)
