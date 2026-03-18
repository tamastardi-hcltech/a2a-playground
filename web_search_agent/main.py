import logging
import os

import uvicorn
from a2a.server.apps.jsonrpc import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from web_search_agent.agent_executor import SearchAgentExecutor

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
# Suppress noisy ddgs provider-level connection logs in constrained networks.
logging.getLogger("ddgs").setLevel(
    os.getenv("DDGS_LOG_LEVEL", "WARNING").upper()
)
logging.getLogger("ddgs.ddgs").setLevel(
    os.getenv("DDGS_LOG_LEVEL", "WARNING").upper()
)


def build_agent_card(agent_url: str) -> AgentCard:
    return AgentCard(
        name="Web Search Agent",
        description="Searches the web and returns concise answers.",
        url=agent_url,
        version="0.1.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="web_search",
                name="Web Search",
                description="Search for up-to-date public information.",
                tags=["search", "web"],
                examples=[
                    "Find the latest TypeScript 5 release notes.",
                    "Summarize recent updates about A2A SDK.",
                ],
            )
        ],
    )


def create_app():
    host = os.getenv("A2A_HOST", "127.0.0.1")
    port = int(os.getenv("A2A_PORT", "8000"))
    agent_url = os.getenv("A2A_AGENT_URL", f"http://{host}:{port}")

    request_handler = DefaultRequestHandler(
        agent_executor=SearchAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    app_builder = A2AFastAPIApplication(
        agent_card=build_agent_card(agent_url),
        http_handler=request_handler,
    )
    return app_builder.build(title="A2A Web Search Agent")


app = create_app()


def run() -> None:
    uvicorn.run(
        app,
        host=os.getenv("A2A_HOST", "127.0.0.1"),
        port=int(os.getenv("A2A_PORT", "8000")),
    )


if __name__ == "__main__":
    run()
