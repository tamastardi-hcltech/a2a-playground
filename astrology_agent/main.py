import logging
import os

import uvicorn
from a2a.server.apps.jsonrpc import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from astrology_agent.agent_executor import AstrologyAgentExecutor

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)


def build_agent_card(agent_url: str) -> AgentCard:
    return AgentCard(
        name="Astrology Agent",
        description="Provides a daily astrology reading from sign or birth date.",
        url=agent_url,
        version="0.1.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="daily_astrology",
                name="Daily Astrology",
                description="Returns daily astrology outlook using zodiac sign/birth date.",
                tags=["astrology", "daily", "horoscope"],
                examples=[
                    "How will my day look? I am leo.",
                    "Daily horoscope for 1993-08-12.",
                ],
            )
        ],
    )


def create_app():
    host = os.getenv("A2A_HOST", "127.0.0.1")
    port = int(os.getenv("A2A_PORT", "8001"))
    agent_url = os.getenv("A2A_AGENT_URL", f"http://{host}:{port}")

    request_handler = DefaultRequestHandler(
        agent_executor=AstrologyAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    app_builder = A2AFastAPIApplication(
        agent_card=build_agent_card(agent_url),
        http_handler=request_handler,
    )
    return app_builder.build(title="A2A Astrology Agent")


app = create_app()


def run() -> None:
    uvicorn.run(
        app,
        host=os.getenv("A2A_HOST", "127.0.0.1"),
        port=int(os.getenv("A2A_PORT", "8001")),
    )


if __name__ == "__main__":
    run()
