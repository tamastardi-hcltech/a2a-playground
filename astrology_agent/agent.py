import datetime as dt
import os
import random
from langchain.agents import create_agent
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

SIGN_DATE_RANGES = (
    ("capricorn", (12, 22), (1, 19)),
    ("aquarius", (1, 20), (2, 18)),
    ("pisces", (2, 19), (3, 20)),
    ("aries", (3, 21), (4, 19)),
    ("taurus", (4, 20), (5, 20)),
    ("gemini", (5, 21), (6, 20)),
    ("cancer", (6, 21), (7, 22)),
    ("leo", (7, 23), (8, 22)),
    ("virgo", (8, 23), (9, 22)),
    ("libra", (9, 23), (10, 22)),
    ("scorpio", (10, 23), (11, 21)),
    ("sagittarius", (11, 22), (12, 21)),
)


def zodiac_from_birth_date(birth_date: dt.date) -> str:
    month = birth_date.month
    day = birth_date.day
    for sign, start, end in SIGN_DATE_RANGES:
        (s_month, s_day), (e_month, e_day) = start, end
        if s_month <= e_month:
            in_range = (month == s_month and day >= s_day) or (
                month == e_month and day <= e_day
            ) or (s_month < month < e_month)
        else:
            in_range = (month == s_month and day >= s_day) or (
                month == e_month and day <= e_day
            ) or (month > s_month or month < e_month)
        if in_range:
            return sign
    return "capricorn"


@tool
def calculate_sign_from_birth_date(birth_date: str) -> str:
    """Calculate zodiac sign from birth date in YYYY-MM-DD format."""
    parsed = dt.date.fromisoformat(birth_date)
    return zodiac_from_birth_date(parsed)


@tool
def get_daily_horoscope_for_sign(sign: str, date: str | None = None) -> str:
    """Generate a synthetic daily horoscope vibe payload for a zodiac sign."""
    normalized_sign = sign.strip().lower()
    horoscope_date = date or dt.date.today().isoformat()
    seed = f"{normalized_sign}:{horoscope_date}"
    rng = random.Random(seed)

    moods = ["hushed", "electric", "restless", "reflective", "mercurial", "bright"]
    omens = [
        "an unfinished conversation may return",
        "a small delay hides a better route",
        "a quiet message carries extra weight",
        "an old idea can unlock a new step",
        "timing matters more than force today",
    ]
    elements = ["water", "fire", "air", "earth", "mist", "shadow"]
    colors = ["silver", "amber", "indigo", "rose", "emerald", "copper"]

    lucky_number = rng.randint(1, 99)
    payload = {
        "sign": normalized_sign,
        "date": horoscope_date,
        "mood": rng.choice(moods),
        "omen": rng.choice(omens),
        "element": rng.choice(elements),
        "lucky_color": rng.choice(colors),
        "lucky_number": lucky_number,
        "intensity": round(rng.uniform(0.2, 0.95), 2),
    }
    return str(payload)


class AstrologyAgent:
    SYSTEM_PROMPT = (
        "You are an astrology oracle for entertainment.\n"
        "- If birth date is provided, call calculate_sign_from_birth_date first.\n"
        "- For daily reading call get_daily_horoscope_for_sign.\n"
        "- If neither sign nor birth date is provided, ask for one clearly.\n"
        "- Write in a mysterious, ambiguous tone.\n"
        "- Do not claim factual certainty.\n"
        "- Keep response concise and include detected sign."
    )

    def __init__(self):
        self.model = ChatOpenAI(
            model=os.getenv("ASTROLOGY_MODEL", "gpt-5"),
            temperature=float(os.getenv("ASTROLOGY_TEMPERATURE", "1.3")),
        )
        self.tools = [calculate_sign_from_birth_date, get_daily_horoscope_for_sign]
        self.graph = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=self.SYSTEM_PROMPT,
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

    def get_daily_reading(self, query: str) -> str:
        try:
            result = self.graph.invoke({"messages": [HumanMessage(content=query)]})
            return self._extract_text(result)
        except Exception as exc:
            return f"Astrology agent failed: {type(exc).__name__}: {exc}"


if __name__ == "__main__":
    agent = AstrologyAgent()
    print(agent.get_daily_reading("How will my day look? My birthday is 1993-08-12."))
