import argparse
import asyncio
import os

import httpx
from a2a.client.client import ClientConfig
from a2a.client.client import ClientEvent
from a2a.client.client_factory import ClientFactory
from a2a.client.errors import A2AClientTimeoutError
from a2a.client.helpers import create_text_message_object
from a2a.types import Message, Role, Task
from a2a.utils.message import get_message_text
from orchestrator_agent.main import run


def _extract_text(event: ClientEvent | Message) -> str:
    if isinstance(event, Message):
        return get_message_text(event)
    task, _update = event
    return _extract_text_from_task(task)


def _extract_text_from_task(task: Task) -> str:
    if task.status.message:
        text = get_message_text(task.status.message)
        if text:
            return text
    if task.history:
        for message in reversed(task.history):
            if message.role == Role.agent:
                text = get_message_text(message)
                if text:
                    return text
    return ""


async def _ask_orchestrator(question: str) -> str:
    orchestrator_url = os.getenv(
        "ORCHESTRATOR_AGENT_URL",
        "http://127.0.0.1:8010",
    )
    timeout_s = float(os.getenv("ORCHESTRATOR_TIMEOUT", "180"))
    httpx_client = httpx.AsyncClient(timeout=timeout_s)
    client_config = ClientConfig(httpx_client=httpx_client, streaming=False)
    client = await ClientFactory.connect(
        orchestrator_url,
        client_config=client_config,
    )
    try:
        message = create_text_message_object(content=question)
        last_text = ""
        async for event in client.send_message(message):
            candidate = _extract_text(event)
            if candidate:
                last_text = candidate
        return last_text or "No response text returned."
    except A2AClientTimeoutError:
        return (
            "Orchestrator request timed out. Check if orchestrator is running and "
            "its downstream agents are reachable."
        )
    finally:
        await client.close()
        await httpx_client.aclose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        nargs="?",
        default="serve",
        choices=("serve", "ask"),
    )
    parser.add_argument("question", nargs="*")
    args = parser.parse_args()

    if args.mode == "serve":
        run()
    else:
        question = " ".join(args.question).strip()
        if not question:
            raise SystemExit('Provide a question, example: python main.py ask "How will my day look?"')
        response = asyncio.run(_ask_orchestrator(question))
        print(response)
