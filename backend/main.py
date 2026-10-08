from fastapi import FastAPI
from pydantic import BaseModel, Field

from .context import build_context
from .llm import generate_json
from .models import LLMQuest, make_quest


app = FastAPI(title="Outside API")


class QuestRequest(BaseModel):
    interests: list[str] = Field(default_factory=list)
    sim_weather: str | None = None
    sim_time: str | None = None


SYSTEM_PROMPT = """
You are Outside, a concise local quest generator.

Generate one small, realistic activity the user can do outside.

Rules:
- Respect the current time and weather.
- Match the user's interests.
- Prefer a nearby event when the context provides a useful event.
- Never invent an event.
- Keep the action practical and specific.
- Keep the quest concise.
- Return ONLY JSON matching the supplied schema.

The application will calculate XP and special-event information separately.
Do not include XP, event IDs, or other fields outside the schema.
"""


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/quest")
def create_quest(request: QuestRequest):
    context = build_context(
        interests=request.interests,
        sim_weather=request.sim_weather,
        sim_time=request.sim_time,
    )

    user_prompt = f"""
Generate one quest from this context:

{context}
"""

    llm_result = generate_json(
        SYSTEM_PROMPT,
        user_prompt,
        LLMQuest.model_json_schema(),
    )

    llm_quest = LLMQuest.model_validate(llm_result)

    event = context.get("nearby_event")

    final_quest = make_quest(
        quest_type=llm_quest.quest_type,
        title=llm_quest.title,
        action=llm_quest.action,
        duration_minutes=llm_quest.duration_minutes,
        reason=llm_quest.reason,
        event=event,
    )

    return final_quest
