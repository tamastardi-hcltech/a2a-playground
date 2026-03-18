import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import InternalError, UnsupportedOperationError
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

from orchestrator_agent.orchestrator import OrchestratorAgent

logger = logging.getLogger(__name__)


class OrchestratorAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.agent = OrchestratorAgent()

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
