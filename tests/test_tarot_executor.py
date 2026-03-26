import unittest
from types import SimpleNamespace
from unittest.mock import patch

from a2a.utils.message import get_message_text

from tarot_agent.agent_executor import TarotAgentExecutor


class _DummyTarotAgent:
    def __init__(self) -> None:
        self.cards = iter(
            [
                "The Star",
                "The Hermit",
                "The Sun",
            ]
        )

    def build_rng(self, query: str):
        return object()

    def draw_random_card(self, rng):
        return next(self.cards)

    def interpret_card(self, question: str, card: str, position: int, total_cards: int) -> str:
        return f"Interpretation for {card} ({position}/{total_cards})"


class _FakeTaskUpdater:
    instances = []

    def __init__(self, event_queue, task_id, context_id):
        self.event_queue = event_queue
        self.task_id = task_id
        self.context_id = context_id
        self.updates = []
        self.completed_message = None
        self.failed_message = None
        _FakeTaskUpdater.instances.append(self)

    async def start_work(self):
        return None

    async def update_status(self, state, message=None, final=False, timestamp=None, metadata=None):
        self.updates.append((state, message, final))

    async def complete(self, message=None):
        self.completed_message = message

    async def failed(self, message=None):
        self.failed_message = message


class TarotExecutorTests(unittest.IsolatedAsyncioTestCase):
    @patch("tarot_agent.agent_executor.TaskUpdater", _FakeTaskUpdater)
    @patch("tarot_agent.agent_executor.TarotAgent", _DummyTarotAgent)
    @patch("tarot_agent.agent_executor.asyncio.sleep")
    async def test_streams_multiple_updates_before_completion(self, _sleep):
        _FakeTaskUpdater.instances.clear()
        executor = TarotAgentExecutor()
        context = SimpleNamespace(
            get_user_input=lambda: "Draw 3 tarot cards for my project.",
            current_task=SimpleNamespace(id="task-1", context_id="ctx-1"),
        )
        event_queue = object()

        with patch.dict(
            "os.environ",
            {
                "TAROT_CARD_COUNT": "3",
                "TAROT_DELAY_MIN_SEC": "0",
                "TAROT_DELAY_MAX_SEC": "0",
            },
            clear=False,
        ):
            await executor.execute(context, event_queue)

        updater = _FakeTaskUpdater.instances[-1]
        self.assertEqual(len(updater.updates), 3)
        self.assertIsNotNone(updater.completed_message)
        final_text = get_message_text(updater.completed_message)
        self.assertIn("Tarot spread complete:", final_text)
        self.assertIn("1. The Star", final_text)
        self.assertIn("2. The Hermit", final_text)
        self.assertIn("3. The Sun", final_text)


if __name__ == "__main__":
    unittest.main()
