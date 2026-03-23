import asyncio
import os
from uuid import uuid4

import httpx
import streamlit as st
from a2a.client.client import ClientConfig, ClientEvent
from a2a.client.client_factory import ClientFactory
from a2a.client.errors import A2AClientTimeoutError
from a2a.types import Message, Part, Role, Task, TaskState, TextPart
from a2a.utils.message import get_message_text
from a2a.utils.parts import get_data_parts


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


def _extract_required_fields(task: Task) -> list[dict]:
    status_message = task.status.message
    if not status_message:
        return []
    payloads = get_data_parts(status_message.parts)
    for payload in payloads:
        if payload.get("type") == "input_required":
            fields = payload.get("required_fields")
            if isinstance(fields, list):
                return [field for field in fields if isinstance(field, dict)]
    return []


async def _ask_orchestrator_async(
    question: str,
    task_id: str | None = None,
    context_id: str | None = None,
) -> dict:
    orchestrator_url = os.getenv("ORCHESTRATOR_AGENT_URL", "http://127.0.0.1:8010")
    timeout_s = float(os.getenv("ORCHESTRATOR_TIMEOUT", "45"))
    httpx_client = httpx.AsyncClient(timeout=timeout_s)
    client_config = ClientConfig(httpx_client=httpx_client, streaming=False)
    client = await ClientFactory.connect(orchestrator_url, client_config=client_config)
    try:
        message = Message(
            role=Role.user,
            message_id=str(uuid4()),
            context_id=context_id,
            task_id=task_id,
            parts=[Part(root=TextPart(text=question))],
        )
        result = {
            "text": "",
            "state": "unknown",
            "task_id": task_id,
            "context_id": context_id,
            "required_fields": [],
        }
        async for event in client.send_message(message):
            candidate = _extract_text(event)
            if candidate:
                result["text"] = candidate

            if not isinstance(event, Message):
                task, _update = event
                result["task_id"] = task.id
                result["context_id"] = task.context_id
                result["state"] = task.status.state.value
                result["required_fields"] = _extract_required_fields(task)

        if not result["text"]:
            result["text"] = "No response text returned."
        return result
    except A2AClientTimeoutError:
        return {
            "text": (
                "Timeout: orchestrator did not respond in time. "
                "Check if orchestrator and downstream agents are running."
            ),
            "state": TaskState.failed.value,
            "task_id": task_id,
            "context_id": context_id,
            "required_fields": [],
        }
    except Exception as exc:
        return {
            "text": f"Orchestrator request failed: {type(exc).__name__}: {exc}",
            "state": TaskState.failed.value,
            "task_id": task_id,
            "context_id": context_id,
            "required_fields": [],
        }
    finally:
        await client.close()
        await httpx_client.aclose()


def ask_orchestrator(
    question: str,
    task_id: str | None = None,
    context_id: str | None = None,
) -> dict:
    return asyncio.run(
        _ask_orchestrator_async(
            question=question,
            task_id=task_id,
            context_id=context_id,
        )
    )


st.set_page_config(page_title="All-Seeing Oracle", page_icon="🔮", layout="centered")
st.title("All-Seeing Oracle")
st.caption("Multi-agent A2A chat UI (astrology + web search + tarot)")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "task_id" not in st.session_state:
    st.session_state.task_id = None
if "context_id" not in st.session_state:
    st.session_state.context_id = None
if "required_fields" not in st.session_state:
    st.session_state.required_fields = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

has_pending_inputs = bool(st.session_state.required_fields)
user_text = st.chat_input(
    "Ask your question...",
    disabled=has_pending_inputs,
)
if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    with st.chat_message("assistant"):
        with st.spinner("Consulting the oracle and its agents..."):
            result = ask_orchestrator(
                user_text,
                task_id=st.session_state.task_id,
                context_id=st.session_state.context_id,
            )
        st.markdown(result["text"])

    st.session_state.messages.append({"role": "assistant", "content": result["text"]})
    st.session_state.task_id = result["task_id"]
    st.session_state.context_id = result["context_id"]
    st.session_state.required_fields = result["required_fields"]
    st.rerun()

if st.session_state.required_fields:
    st.subheader("More input needed")
    with st.form("required_input_form"):
        field_values: dict[str, str] = {}
        for field in st.session_state.required_fields:
            field_id = str(field.get("id", "field"))
            label = str(field.get("label", field_id))
            hint = str(field.get("format", ""))
            placeholder = str(field.get("example", ""))
            field_values[field_id] = st.text_input(
                label=label,
                placeholder=placeholder,
                help=hint or None,
            )
        submitted = st.form_submit_button("Send required input")

    if submitted:
        missing = [k for k, v in field_values.items() if not v.strip()]
        if missing:
            st.warning(f"Please fill all required fields: {', '.join(missing)}")
        else:
            followup = "\n".join(f"{k}: {v.strip()}" for k, v in field_values.items())
            st.session_state.messages.append({"role": "user", "content": followup})
            with st.chat_message("user"):
                st.markdown(followup)
            with st.chat_message("assistant"):
                with st.spinner("Resuming the oracle reading..."):
                    result = ask_orchestrator(
                        followup,
                        task_id=st.session_state.task_id,
                        context_id=st.session_state.context_id,
                    )
                st.markdown(result["text"])
            st.session_state.messages.append({"role": "assistant", "content": result["text"]})
            st.session_state.task_id = result["task_id"]
            st.session_state.context_id = result["context_id"]
            st.session_state.required_fields = result["required_fields"]
            st.rerun()
