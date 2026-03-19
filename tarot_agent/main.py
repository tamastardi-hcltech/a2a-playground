import logging
import os

import uvicorn
from a2a.server.apps.jsonrpc import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from tarot_agent.agent_executor import TarotAgentExecutor

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)


def build_agent_card(agent_url: str) -> AgentCard:
    return AgentCard(
        name="Tarot Stream Agent",
        description="Draws tarot cards and streams each reveal with a delay.",
        url=agent_url,
        version="0.1.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id="tarot_stream",
                name="Tarot Streaming Draw",
                description="Reveals cards one-by-one as task updates.",
                tags=["tarot", "streaming", "oracle"],
                examples=[
                    "Draw 3 cards for my week.",
                    "Give me a tarot spread for this project.",
                ],
            )
        ],
    )


def create_app():
    host = os.getenv("A2A_HOST", "127.0.0.1")
    port = int(os.getenv("A2A_PORT", "8002"))
    agent_url = os.getenv("A2A_AGENT_URL", f"http://{host}:{port}")

    request_handler = DefaultRequestHandler(
        agent_executor=TarotAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    app_builder = A2AFastAPIApplication(
        agent_card=build_agent_card(agent_url),
        http_handler=request_handler,
    )
    return app_builder.build(title="A2A Tarot Stream Agent")


app = create_app()


def run() -> None:
    uvicorn.run(
        app,
        host=os.getenv("A2A_HOST", "127.0.0.1"),
        port=int(os.getenv("A2A_PORT", "8002")),
    )


if __name__ == "__main__":
    run()
