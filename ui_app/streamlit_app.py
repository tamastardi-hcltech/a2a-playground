import asyncio
import os

import httpx
import streamlit as st
from a2a.client.client import ClientConfig, ClientEvent
from a2a.client.client_factory import ClientFactory
from a2a.client.errors import A2AClientTimeoutError
from a2a.client.helpers import create_text_message_object
from a2a.types import Message, Role, Task
from a2a.utils.message import get_message_text


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


async def _ask_orchestrator_async(question: str) -> str:
    orchestrator_url = os.getenv("ORCHESTRATOR_AGENT_URL", "http://127.0.0.1:8010")
    timeout_s = float(os.getenv("ORCHESTRATOR_TIMEOUT", "1800"))
    httpx_client = httpx.AsyncClient(timeout=timeout_s)
    client_config = ClientConfig(httpx_client=httpx_client, streaming=False)
    client = await ClientFactory.connect(orchestrator_url, client_config=client_config)
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
            "Timeout: orchestrator did not respond in time. "
            "Check if orchestrator and downstream agents are running."
        )
    except Exception as exc:
        return f"Orchestrator request failed: {type(exc).__name__}: {exc}"
    finally:
        await client.close()
        await httpx_client.aclose()


def ask_orchestrator(question: str) -> str:
    return asyncio.run(_ask_orchestrator_async(question))


st.set_page_config(page_title="All-Seeing Oracle", page_icon="🔮", layout="centered")
st.title("All-Seeing Oracle")
st.caption("Multi-agent A2A chat UI (astrology + web search + tarot)")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_text = st.chat_input("Ask your question...")
if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    with st.chat_message("assistant"):
        with st.spinner("Consulting the oracle and its agents..."):
            response = ask_orchestrator(user_text)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
