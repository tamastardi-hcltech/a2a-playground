import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import InternalError, UnsupportedOperationError
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

from astrology_agent.agent import AstrologyAgent

logger = logging.getLogger(__name__)


class AstrologyAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.agent: AstrologyAgent | None = None

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        if self.agent is None:
            self.agent = AstrologyAgent()
        query = context.get_user_input()
        logger.info("astrology request received: %s", query)
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
            response = self.agent.get_daily_reading(query)
            logger.info("astrology response produced: %s", response)
            message = new_agent_text_message(response, task.context_id, task.id)
            await task_updater.complete(message=message)
        except Exception as exc:
            logger.exception("astrology execution failed: %s", exc)
            message = new_agent_text_message(
                f"Astrology reading failed: {exc}",
                task.context_id,
                task.id,
            )
            await task_updater.failed(message=message)
            raise ServerError(error=InternalError(message=str(exc))) from exc

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise ServerError(error=UnsupportedOperationError())
