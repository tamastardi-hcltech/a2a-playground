import unittest
from types import SimpleNamespace

from a2a.types import DataPart, Part, Role, TextPart

from orchestrator_agent.agent_executor import OrchestratorAgentExecutor


def _user_message(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        role=Role.user,
        parts=[SimpleNamespace(root=TextPart(text=text))],
    )


def _task_with_pending_birth_date(history_text: str) -> SimpleNamespace:
    return SimpleNamespace(
        history=[_user_message(history_text)],
        status=SimpleNamespace(
            message=SimpleNamespace(
                parts=[
                    Part(root=DataPart(data={
                        "type": "input_required",
                        "required_fields": [
                            {
                                "id": "birth_date",
                                "label": "Birth date",
                            }
                        ],
                    }))
                ]
            )
        ),
    )


def _task_with_birth_date_request_in_history(history_text: str) -> SimpleNamespace:
    return SimpleNamespace(
        history=[
            _user_message(history_text),
            SimpleNamespace(
                role=Role.agent,
                parts=[
                    Part(root=DataPart(data={
                        "type": "input_required",
                        "required_fields": [
                            {
                                "id": "birth_date",
                                "label": "Birth date",
                            }
                        ],
                    }))
                ],
            ),
        ],
        status=SimpleNamespace(message=None),
    )


class BirthDateGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.executor = OrchestratorAgentExecutor.__new__(OrchestratorAgentExecutor)
        self.executor._input_gate_model = SimpleNamespace(
            invoke=lambda _messages: SimpleNamespace(result="YES")
        )

    def test_requests_birth_date_when_gate_model_says_astrology_is_needed(self):
        task = SimpleNamespace(history=[_user_message("How will my day look?")])
        needs_birth_date = self.executor._should_request_birth_date(
            query="How will my day look?",
            task=task,
        )
        self.assertTrue(needs_birth_date)

    def test_does_not_request_birth_date_when_gate_model_says_no(self):
        self.executor._input_gate_model = SimpleNamespace(
            invoke=lambda _messages: SimpleNamespace(result="NO")
        )
        task = SimpleNamespace(history=[_user_message("How will my day look if I am cancer?")])
        needs_birth_date = self.executor._should_request_birth_date(
            query="How will my day look if I am cancer?",
            task=task,
        )
        self.assertFalse(needs_birth_date)

    def test_follow_up_birth_date_still_respects_gate_model_answer(self):
        self.executor._input_gate_model = SimpleNamespace(
            invoke=lambda _messages: SimpleNamespace(result="NO")
        )
        task = _task_with_pending_birth_date("Can you give me my horoscope?")
        needs_birth_date = self.executor._should_request_birth_date(
            query="birth_date: 1993-08-12",
            task=task,
        )
        self.assertFalse(needs_birth_date)

    def test_follow_up_does_not_reask_even_if_gate_model_would_say_yes(self):
        self.executor._input_gate_model = SimpleNamespace(
            invoke=lambda _messages: SimpleNamespace(result="YES")
        )
        task = _task_with_pending_birth_date("Can you give me my horoscope?")
        needs_birth_date = self.executor._should_request_birth_date(
            query="birth_date: 1993-08-12",
            task=task,
        )
        self.assertFalse(needs_birth_date)

    def test_follow_up_does_not_reask_when_request_only_exists_in_history(self):
        self.executor._input_gate_model = SimpleNamespace(
            invoke=lambda _messages: SimpleNamespace(result="YES")
        )
        task = _task_with_birth_date_request_in_history("Can you give me my horoscope?")
        needs_birth_date = self.executor._should_request_birth_date(
            query="birth_date: 1993-08-12",
            task=task,
        )
        self.assertFalse(needs_birth_date)


if __name__ == "__main__":
    unittest.main()
