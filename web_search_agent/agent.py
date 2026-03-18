import os

from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain.agents import create_agent
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI


class SearchAgent:
    SYSTEM_PROMPT = ("You are a search agent, that tries to find relevant data using the DuckDuckGo search engine"
                     "Be sure to add all the citations for the provided information.")

    def __init__(self):
        self.model = ChatOpenAI(
            model=os.getenv("SEARCH_MODEL", "gpt-5"),
            temperature=0
        )
        ddg_wrapper = DuckDuckGoSearchAPIWrapper(
            backend=os.getenv("DDG_BACKEND", "duckduckgo"),
            max_results=int(os.getenv("DDG_MAX_RESULTS", "5")),
            region=os.getenv("DDG_REGION", "wt-wt"),
            time=os.getenv("DDG_TIME", "y"),
        )
        self.tools = [DuckDuckGoSearchRun(api_wrapper=ddg_wrapper)]
        self.graph = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=self.SYSTEM_PROMPT
        )

    def _extract_text(self, result: object) -> str:
        if isinstance(result, str):
            return result

        if isinstance(result, dict):
            messages = result.get("messages")
            if isinstance(messages, list) and messages:
                last_message = messages[-1]
                if isinstance(last_message, BaseMessage):
                    content = last_message.content
                    if isinstance(content, str):
                        return content
                    if isinstance(content, list):
                        chunks = []
                        for item in content:
                            if isinstance(item, dict):
                                text = item.get("text")
                                if isinstance(text, str):
                                    chunks.append(text)
                        if chunks:
                            return "\n".join(chunks)

        return str(result)

    def get_agent_response(self, query: str) -> str:
        try:
            result = self.graph.invoke({"messages": [HumanMessage(content=query)]})
            return self._extract_text(result)
        except Exception as exc:
            return (
                "Search backend is currently unavailable "
                f"({type(exc).__name__}: {exc})."
            )



if __name__ == '__main__':
    query = "cancer zodiac"
    agent = SearchAgent()
    print(agent.get_agent_response(query))
