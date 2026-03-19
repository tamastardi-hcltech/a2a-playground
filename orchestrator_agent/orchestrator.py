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

        self.astrology_card_url = f"{astrology_base_url}/.well-known/agent-card.json"
        self.search_card_url = f"{search_base_url}/.well-known/agent-card.json"
        self.tarot_card_url = f"{tarot_base_url}/.well-known/agent-card.json"

        astrology_remote = RemoteA2aAgent(
            name="astrology_remote",
            agent_card=self.astrology_card_url,
            description="Remote astrology A2A agent",
            timeout=remote_timeout,
        )
        search_remote = RemoteA2aAgent(
            name="web_search_remote",
            agent_card=self.search_card_url,
            description="Remote web search A2A agent",
            timeout=remote_timeout,
        )
        tarot_remote = RemoteA2aAgent(
            name="tarot_stream_remote",
            agent_card=self.tarot_card_url,
            description="Remote tarot streaming A2A agent",
            timeout=remote_timeout,
        )

        self._coordinator_agent = Agent(
            name="orchestrator_coordinator",
            model=os.getenv("ORCHESTRATOR_MODEL", "openai/gpt-5"),
            instruction=(
                "You are the All-Seeing Oracle, a coordinating intelligence that reaches into remote agents.\n"
                "You must consult your full toolkit before your final answer.\n"
                "Required workflow for each user request:\n"
                "1. Call astrology_remote at least once.\n"
                "2. Call web_search_remote at least once.\n"
                "3. Call tarot_stream_remote at least once.\n"
                "4. If needed, call any remote agent additional times to refine or cross-check signals.\n"
                "5. Synthesize all gathered signals into one coherent oracle answer.\n"
                "If any tool fails or times out, continue with the remaining tools and explicitly note what was unavailable.\n"
                "Persona and style:\n"
                "- Mystical, ambiguous, and evocative, but still understandable.\n"
                "- Speak in plain text only.\n"
                "- Never output JSON or schema blocks.\n"
                "- If signals conflict, acknowledge the tension instead of forcing certainty.\n"
                "- Do not skip tools unless they are unavailable.\n"
                "- Use follow-up tool calls when the question is ambiguous, underspecified, or evidence is thin.\n"
                "- Do not provide a final answer before tool calls are attempted."
            ),
            tools=[
                AgentTool(astrology_remote),
                AgentTool(search_remote),
                AgentTool(tarot_remote),
            ],
        )

        self._adk_session_service = InMemorySessionService()
        self._runner = Runner(
            app_name="orchestrator_adk",
            agent=self._coordinator_agent,
            session_service=self._adk_session_service,
        )
        self._adk_user_id = os.getenv("ORCHESTRATOR_ADK_USER_ID", "local_user")

    async def get_orchestrated_response(self, user_query: str) -> str:
        logger.info("orchestrator request received: %s", user_query)
        session_id = str(uuid.uuid4())
        await self._adk_session_service.create_session(
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

        resolved = (
                last_text
                or "Orchestrator produced no text output."
        )
        logger.info("orchestrator response produced: %s", resolved)
        return resolved
