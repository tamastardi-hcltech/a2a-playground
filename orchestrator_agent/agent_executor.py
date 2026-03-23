import logging
import os

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import DataPart, InternalError, Message, Part, Role, Task, TextPart, UnsupportedOperationError
from a2a.utils import new_agent_parts_message, new_agent_text_message, new_task
from a2a.utils.errors import ServerError
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from orchestrator_agent.orchestrator import OrchestratorAgent

logger = logging.getLogger(__name__)


class OrchestratorAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.agent = OrchestratorAgent()
        self._input_gate_model = ChatOpenAI(
            model=os.getenv("ORCHESTRATOR_INPUT_GATE_MODEL", "gpt-5-mini"),
            temperature=0,
        )

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
        history_snippets: list[str] = []
        if task and task.history:
            for msg in task.history:
                if msg.role != Role.user:
                    continue
                for part in msg.parts:
                    if isinstance(part.root, TextPart):
                        history_snippets.append(part.root.text)
        history_text = "\n".join(history_snippets[-8:])

        system_prompt = (
            "You are a strict gatekeeper for an oracle orchestrator.\n"
            "Decide if we must ask the user for birth date before proceeding.\n"
            "Return exactly one token: YES or NO.\n"
            "Return YES only when:\n"
            "- the request is personal guidance where astrology is relevant, and\n"
            "- no birth date is present in the user conversation context.\n"
            "Return NO for non-personal/general questions, or when birth date already exists."
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
            text = ""
            if isinstance(result.content, str):
                text = result.content
            elif isinstance(result.content, list):
                chunks = []
                for item in result.content:
                    if isinstance(item, dict):
                        value = item.get("text")
                        if isinstance(value, str):
                            chunks.append(value)
                text = "\n".join(chunks)
            return text.strip().upper().startswith("YES")
        except Exception as exc:
            logger.warning("input gate model failed, defaulting to NO: %s", exc)
            return False
