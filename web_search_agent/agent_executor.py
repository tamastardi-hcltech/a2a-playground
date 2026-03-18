import logging

from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import InternalError, UnsupportedOperationError
from a2a.utils import new_task, new_agent_text_message
from a2a.utils.errors import ServerError

from web_search_agent.agent import SearchAgent

logger = logging.getLogger(__name__)


class SearchAgentExecutor(AgentExecutor):

    def __init__(self):
        self.agent: SearchAgent | None = None


    async def execute(self, context: RequestContext, event_queue: EventQueue):
        if self.agent is None:
            self.agent = SearchAgent()
        query = context.get_user_input()
        logger.info("web_search request received: %s", query)
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
            response = self.agent.get_agent_response(query)
            logger.info("web_search response produced: %s", response)
            message = new_agent_text_message(response, task.context_id, task.id)
            await task_updater.complete(message=message)
        except Exception as e:
            logger.exception("web_search execution failed: %s", e)
            message = new_agent_text_message(
                f"Search failed: {e}",
                task.context_id,
                task.id,
            )
            await task_updater.failed(message=message)
            raise ServerError(error=InternalError(message=str(e))) from e

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise ServerError(error=UnsupportedOperationError())
