import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from orchestrator_agent.orchestrator import OrchestratorAgent


class _DummyRemoteA2aAgent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _DummyAgentTool:
    def __init__(self, remote):
        self.remote = remote


class _DummyAgent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _DummySessionService:
    def __init__(self):
        self.create_session = AsyncMock()


class _DummyRunner:
    def __init__(self, app_name, agent, session_service):
        self.app_name = app_name
        self.agent = agent
        self.session_service = session_service
        self._events = []

    async def run_async(self, **_kwargs):
        for event in self._events:
            yield event


class OrchestratorResponseTests(unittest.IsolatedAsyncioTestCase):
    @patch("orchestrator_agent.orchestrator.Runner", _DummyRunner)
    @patch("orchestrator_agent.orchestrator.InMemorySessionService", _DummySessionService)
    @patch("orchestrator_agent.orchestrator.Agent", _DummyAgent)
    @patch("orchestrator_agent.orchestrator.AgentTool", _DummyAgentTool)
    @patch("orchestrator_agent.orchestrator.RemoteA2aAgent", _DummyRemoteA2aAgent)
    async def test_collects_last_text_chunk_from_adk_runner(self):
        agent = OrchestratorAgent()
        agent._runner._events = [
            SimpleNamespace(content=SimpleNamespace(parts=[SimpleNamespace(text="Consulted agents:\n- Web Search Agent: Needed current facts.")])),
            SimpleNamespace(content=SimpleNamespace(parts=[SimpleNamespace(text="Consulted agents:\n- Web Search Agent: Needed current facts.\n\nOracle synthesis:\nThe signal is clear.")])),
        ]

        response = await agent.get_orchestrated_response("Find the latest TypeScript release notes.")

        self.assertIn("Consulted agents:", response)
        self.assertIn("Oracle synthesis:", response)
        agent._session_service.create_session.assert_awaited()

    @patch("orchestrator_agent.orchestrator.Runner", _DummyRunner)
    @patch("orchestrator_agent.orchestrator.InMemorySessionService", _DummySessionService)
    @patch("orchestrator_agent.orchestrator.Agent", _DummyAgent)
    @patch("orchestrator_agent.orchestrator.AgentTool", _DummyAgentTool)
    @patch("orchestrator_agent.orchestrator.RemoteA2aAgent", _DummyRemoteA2aAgent)
    async def test_returns_default_message_when_runner_has_no_text(self):
        agent = OrchestratorAgent()
        agent._runner._events = [SimpleNamespace(content=None)]

        response = await agent.get_orchestrated_response("How is my week looking?")

        self.assertEqual(response, "Orchestrator produced no text output.")


if __name__ == "__main__":
    unittest.main()
