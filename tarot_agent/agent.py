import os
import random

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


MAJOR_ARCANA = [
    "The Fool",
    "The Magician",
    "The High Priestess",
    "The Empress",
    "The Emperor",
    "The Hierophant",
    "The Lovers",
    "The Chariot",
    "Strength",
    "The Hermit",
    "Wheel of Fortune",
    "Justice",
    "The Hanged Man",
    "Death",
    "Temperance",
    "The Devil",
    "The Tower",
    "The Star",
    "The Moon",
    "The Sun",
    "Judgement",
    "The World",
]

SUITS = ["Wands", "Cups", "Swords", "Pentacles"]
RANKS = [
    "Ace",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Page",
    "Knight",
    "Queen",
    "King",
]


class TarotAgent:
    def __init__(self) -> None:
        self.deck = MAJOR_ARCANA + [f"{rank} of {suit}" for suit in SUITS for rank in RANKS]
        self.model = ChatOpenAI(
            model=os.getenv("TAROT_MODEL", "gpt-5"),
            temperature=float(os.getenv("TAROT_TEMPERATURE", "1.1")),
        )

    def draw_next_tarot_card(self) -> str:
        return random.choice(self.deck)

    def draw_random_card(self) -> str:
        return self.draw_next_tarot_card()

    def interpret_card(
        self,
        question: str,
        card: str,
        position: int,
        total_cards: int,
    ) -> str:
        system_prompt = (
            "You are a tarot reader. Give a concise, atmospheric interpretation "
            "for one card in context of the user's question. "
            "Keep it to 2-4 sentences, plain text."
        )
        user_prompt = (
            f"Question: {question}\n"
            f"Card: {card}\n"
            f"Position: {position}/{total_cards}\n"
            "Interpret this card now."
        )
        result = self.model.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        return self._extract_text(result)

    def _extract_text(self, result: object) -> str:
        if isinstance(result, str):
            return result
        if isinstance(result, BaseMessage):
            content = result.content
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
