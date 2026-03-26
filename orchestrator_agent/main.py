import logging
import os

import uvicorn
from a2a.server.apps.jsonrpc import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from orchestrator_agent.agent_executor import OrchestratorAgentExecutor

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)


def build_agent_card(agent_url: str) -> AgentCard:
    return AgentCard(
        name="All-Seeing Oracle",
        description=(
            "A multi-agent oracle that selectively consults astrology, web search, "
            "and tarot remotes when they fit the request before returning one blended prophecy."
        ),
        url=agent_url,
        version="0.1.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="multi_agent_orchestration",
                name="Oracle Synthesis",
                description=(
                    "Chooses the relevant oracle signals (astrology, web search, tarot) "
                    "and fuses them into one mysterious answer."
                ),
                tags=["oracle", "orchestration", "multi-agent", "synthesis"],
                examples=[
                    "How will my day look?",
                    "How is my current project going to work out?",
                    "What hidden pattern should I watch this week?",
                ],
            )
        ],
    )


def create_app():
    host = os.getenv("A2A_HOST", "127.0.0.1")
    port = int(os.getenv("A2A_PORT", "8010"))
    agent_url = os.getenv("A2A_AGENT_URL", f"http://{host}:{port}")

    request_handler = DefaultRequestHandler(
        agent_executor=OrchestratorAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    app_builder = A2AFastAPIApplication(
        agent_card=build_agent_card(agent_url),
        http_handler=request_handler,
    )
    return app_builder.build(title="A2A Orchestrator Agent")


app = create_app()


def run() -> None:
    uvicorn.run(
        app,
        host=os.getenv("A2A_HOST", "127.0.0.1"),
        port=int(os.getenv("A2A_PORT", "8010")),
    )


if __name__ == "__main__":
    run()
