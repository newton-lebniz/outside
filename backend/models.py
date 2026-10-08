from typing import Literal
from pydantic import BaseModel

QuestType = Literal[
    "movement",
    "nature",
    "social",
    "sky",
    "exploration",
]


class LLMQuest(BaseModel):
    """What the model is asked to produce."""

    quest_type: QuestType
    title: str
    action: str
    duration_minutes: int
    reason: str


def xp_for(duration_minutes):
    return min(200, 50 + 5 * duration_minutes)


def make_quest(
    quest_type,
    title,
    action,
    duration_minutes,
    reason,
    event=None,
):
    """The final quest object the rest of the app uses (LLM or fallback)."""

    quest = {
        "quest_type": quest_type,
        "title": title,
        "action": action,
        "duration_minutes": duration_minutes,
        "reason": reason,
        "xp": xp_for(duration_minutes),
        "is_special": False,
        "event_id": None,
        "walk_minutes": None,
    }

    if event:
        quest.update(
            quest_type=event["quest_type"],
            is_special=True,
            event_id=event["id"],
            walk_minutes=event["walk_minutes"],
            xp=500,
        )

    return quest
