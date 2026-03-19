import asyncio
import logging
import os
import random

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import InternalError, TaskState, UnsupportedOperationError
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

from tarot_agent.agent import TarotAgent

logger = logging.getLogger(__name__)


class TarotAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.agent = TarotAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        query = context.get_user_input()
        logger.info("tarot request received: %s", query)
        task = context.current_task

        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await updater.start_work()

        try:
            num_cards = int(os.getenv("TAROT_CARD_COUNT", "3"))
            delay_min = int(os.getenv("TAROT_DELAY_MIN_SEC", "5"))
            delay_max = int(os.getenv("TAROT_DELAY_MAX_SEC", "15"))
            if delay_min > delay_max:
                delay_min, delay_max = delay_max, delay_min

            num_cards = max(1, min(num_cards, 10))
            drawn_cards: set[str] = set()
            interpretations: list[tuple[str, str]] = []

            for index in range(1, num_cards + 1):
                card = self.agent.draw_random_card()
                while card in drawn_cards:
                    card = self.agent.draw_random_card()
                drawn_cards.add(card)
                if index > 1:
                    await asyncio.sleep(random.randint(delay_min, delay_max))
                interpretation = self.agent.interpret_card(
                    question=query,
                    card=card,
                    position=index,
                    total_cards=num_cards,
                )
                interpretations.append((card, interpretation))
                reveal = (
                    f"Card {index}/{num_cards}: {card}\n"
                    f"Reading: {interpretation}"
                )
                logger.info("tarot streamed reveal: %s", reveal)
                await updater.update_status(
                    TaskState.working,
                    message=new_agent_text_message(
                        reveal,
                        task.context_id,
                        task.id,
                    ),
                    final=False,
                )

            final_text = (
                "Tarot spread complete:\n"
                + "\n\n".join(
                    f"{i + 1}. {card}\n{reading}"
                    for i, (card, reading) in enumerate(interpretations)
                )
            )
            logger.info("tarot final response: %s", final_text)
            await updater.complete(
                message=new_agent_text_message(final_text, task.context_id, task.id)
            )
        except Exception as exc:
            logger.exception("tarot execution failed: %s", exc)
            await updater.failed(
                message=new_agent_text_message(
                    f"Tarot reading failed: {exc}",
                    task.context_id,
                    task.id,
                )
            )
            raise ServerError(error=InternalError(message=str(exc))) from exc

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise ServerError(error=UnsupportedOperationError())
