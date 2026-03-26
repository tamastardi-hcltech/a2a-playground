import logging
import os
from typing import Literal

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    DataPart,
    InternalError,
    Part,
    Role,
    Task,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import new_agent_parts_message, new_agent_text_message, new_task
from a2a.utils.errors import ServerError
from a2a.utils.parts import get_data_parts
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from orchestrator_agent.orchestrator import OrchestratorAgent

logger = logging.getLogger(__name__)


class BirthDateGateResult(BaseModel):
    result: Literal["YES", "NO"]


class OrchestratorAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.agent = OrchestratorAgent()
        self._input_gate_model = ChatOpenAI(
            model=os.getenv("ORCHESTRATOR_INPUT_GATE_MODEL", "gpt-4o-mini"),
            temperature=0,
        ).with_structured_output(BirthDateGateResult)

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        query = context.get_user_input()
        logger.info("orchestrator request received: %s", query)
        task = context.current_task

        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        task_updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await task_updater.start_work()

        try:
            if self._should_request_birth_date(query, task):
                prompt_text = (
                    "Before I read your path through astrology, I need your birth date.\n"
                    "Please provide it in YYYY-MM-DD format."
                )
                data_payload = {
                    "type": "input_required",
                    "required_fields": [
                        {
                            "id": "birth_date",
                            "label": "Birth date",
                            "format": "YYYY-MM-DD",
                            "example": "1993-08-12",
                        }
                    ],
                }
                message = new_agent_parts_message(
                    [
                        Part(root=TextPart(text=prompt_text)),
                        Part(root=DataPart(data=data_payload)),
                    ],
                    task.context_id,
                    task.id,
                )
                logger.info("orchestrator input-required: birth_date")
                await task_updater.requires_input(message=message, final=False)
                return

            await task_updater.update_status(
                TaskState.working,
                message=new_agent_text_message(
                    "The oracle is deciding which remote signals matter for this request.",
                    task.context_id,
                    task.id,
                ),
                final=False,
            )

            response = await self.agent.get_orchestrated_response(query)
            logger.info("orchestrator response produced: %s", response)
            message = new_agent_text_message(response, task.context_id, task.id)
            await task_updater.complete(message=message)
        except Exception as exc:
            logger.exception("orchestrator execution failed: %s", exc)
            message = new_agent_text_message(
                f"Orchestration failed: {exc}",
                task.context_id,
                task.id,
            )
            await task_updater.failed(message=message)
            raise ServerError(error=InternalError(message=str(exc))) from exc

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise ServerError(error=UnsupportedOperationError())

    def _should_request_birth_date(self, query: str, task: Task | None) -> bool:
        if self._is_birth_date_follow_up(task, query):
            return False

        history_text = self._get_user_history_text(task)
        system_prompt = (
            "You are a strict gatekeeper for an oracle orchestrator.\n"
            "Decide whether the main oracle is likely to need astrology for this request.\n"
            "Return exactly one token: YES or NO.\n"
            "Return YES only when astrology is likely relevant and a birth date would materially improve the result.\n"
            "Return NO for requests that can be handled without astrology."
        )
        user_prompt = (
            f"Conversation user history:\n{history_text or '(none)'}\n\n"
            f"Current user message:\n{query}\n\n"
            "Answer:"
        )
        try:
            result = self._input_gate_model.invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            return result.result == "YES"
        except Exception as exc:
            logger.warning("input gate model failed, defaulting to NO: %s", exc)
            return False

    def _is_birth_date_follow_up(self, task: Task | None, query: str) -> bool:
        if not task or not query.strip():
            return False

        status_message = getattr(getattr(task, "status", None), "message", None)
        if status_message and self._message_requests_birth_date(status_message):
            return True

        if task.history:
            for message in reversed(task.history):
                if message.role != Role.agent:
                    continue
                if self._message_requests_birth_date(message):
                    return True
        return False

    def _message_requests_birth_date(self, message) -> bool:
        for payload in get_data_parts(message.parts):
            if payload.get("type") != "input_required":
                continue
            fields = payload.get("required_fields")
            if not isinstance(fields, list):
                continue
            for field in fields:
                if isinstance(field, dict) and field.get("id") == "birth_date":
                    return True
        return False

    def _get_user_history_text(self, task: Task | None) -> str:
        history_snippets: list[str] = []
        if task and task.history:
            for msg in task.history:
                if msg.role != Role.user:
                    continue
                for part in msg.parts:
                    if isinstance(part.root, TextPart):
                        history_snippets.append(part.root.text)
        return "\n".join(history_snippets[-8:])
