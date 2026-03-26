import logging
import os
import uuid

from google.adk import Agent, Runner
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.sessions import InMemorySessionService
from google.adk.tools import AgentTool
from google.genai import types as genai_types

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    def __init__(self) -> None:
        remote_timeout = float(os.getenv("ORCHESTRATOR_REMOTE_TIMEOUT", "1800"))
        astrology_base_url = os.getenv(
            "ASTROLOGY_AGENT_URL",
            "http://127.0.0.1:8001",
        ).rstrip("/")
        search_base_url = os.getenv(
            "WEB_SEARCH_AGENT_URL",
            "http://127.0.0.1:8000",
        ).rstrip("/")
        tarot_base_url = os.getenv(
            "TAROT_AGENT_URL",
            "http://127.0.0.1:8002",
        ).rstrip("/")

        astrology_remote = RemoteA2aAgent(
            name="astrology_remote",
            agent_card=f"{astrology_base_url}/.well-known/agent-card.json",
            description="Remote astrology A2A agent",
            timeout=remote_timeout,
        )
        search_remote = RemoteA2aAgent(
            name="web_search_remote",
            agent_card=f"{search_base_url}/.well-known/agent-card.json",
            description="Remote web search A2A agent",
            timeout=remote_timeout,
        )
        tarot_remote = RemoteA2aAgent(
            name="tarot_stream_remote",
            agent_card=f"{tarot_base_url}/.well-known/agent-card.json",
            description="Remote tarot streaming A2A agent",
            timeout=remote_timeout,
        )

        self._coordinator_agent = Agent(
            name="orchestrator_coordinator",
            model=os.getenv("ORCHESTRATOR_MODEL", "openai/gpt-5"),
            instruction=(
                "You are the All-Seeing Oracle, a coordinating intelligence that can consult remote A2A agents.\n"
                "Available tools:\n"
                "- astrology_remote: zodiac signs, horoscopes, birth-date based readings, astrology framing\n"
                "- web_search_remote: current facts, external information, release notes, web-backed questions\n"
                "- tarot_stream_remote: tarot, reflective guidance, intuitive pattern-finding, divination-style questions\n"
                "Use only the tools that genuinely help with the user's request. Do not call every tool by default.\n"
                "If a request is clearly factual, prefer web_search_remote.\n"
                "If a request is astrology-specific, use astrology_remote.\n"
                "If a request is reflective or explicitly tarot-oriented, use tarot_stream_remote.\n"
                "For mixed requests, you may call multiple relevant tools.\n"
                "If a tool fails or times out, continue with the remaining tools and note the missing signal.\n"
                "Your final answer must be plain text and structured like this:\n"
                "Consulted agents:\n"
                "- <agent>: <why it was used>\n"
                "Intentionally skipped:\n"
                "- <agent>: <why it was not needed>\n"
                "Oracle synthesis:\n"
                "<final answer>\n"
                "Only list agents under Consulted if you actually used them.\n"
                "Only list agents under Intentionally skipped if they were available but not needed.\n"
                "Keep the synthesis understandable, concise, and honest about uncertainty."
            ),
            tools=[
                AgentTool(astrology_remote),
                AgentTool(search_remote),
                AgentTool(tarot_remote),
            ],
        )

        self._session_service = InMemorySessionService()
        self._runner = Runner(
            app_name="orchestrator_adk",
            agent=self._coordinator_agent,
            session_service=self._session_service,
        )
        self._adk_user_id = os.getenv("ORCHESTRATOR_ADK_USER_ID", "local_user")

    async def get_orchestrated_response(self, user_query: str) -> str:
        logger.info("orchestrator request received: %s", user_query)
        session_id = str(uuid.uuid4())
        await self._session_service.create_session(
            app_name=self._runner.app_name,
            user_id=self._adk_user_id,
            session_id=session_id,
        )
        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=user_query)],
        )

        last_text = ""
        async for event in self._runner.run_async(
                user_id=self._adk_user_id,
                session_id=session_id,
                new_message=content,
        ):
            if event.content and event.content.parts:
                chunks = [part.text for part in event.content.parts if part.text]
                if chunks:
                    last_text = "\n".join(chunks)

        resolved = last_text or "Orchestrator produced no text output."
        logger.info("orchestrator response produced: %s", resolved)
        return resolved
