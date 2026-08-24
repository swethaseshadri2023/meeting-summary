"""
LLM summarization layer.

Takes a raw meeting transcript and returns:
  - summary: short paragraph overview
  - key_decisions: list of strings
  - action_items: list of {owner, task, due_date}

Uses Claude via the Anthropic Messages API and asks for strict JSON output
so the result can be reliably parsed and stored / rendered by the frontend.
"""
import json
import re
from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

SYSTEM_PROMPT = """You are an expert meeting analyst. You will be given a raw \
meeting transcript (which may include ASR errors, filler words, or unclear \
speaker attribution). Your job is to produce a clean, action-oriented summary.

Respond with ONLY valid JSON (no markdown fences, no commentary) in exactly \
this shape:

{
  "summary": "2-4 sentence plain-language overview of what the meeting was about and what was accomplished",
  "key_decisions": ["decision 1", "decision 2"],
  "action_items": [
    {"owner": "person or team responsible, or 'Unassigned' if unclear", "task": "clear, specific task description", "due_date": "date if mentioned, otherwise 'Not specified'"}
  ]
}

Rules:
- Base everything strictly on the transcript content; do not invent facts.
- If no clear decisions were made, return an empty list for key_decisions.
- If no clear action items exist, return an empty list for action_items.
- Keep each action item specific enough that someone could act on it without re-reading the transcript.
"""

USER_PROMPT_TEMPLATE = (
    "Summarize this meeting transcript into key decisions and action items.\n\n"
    "TRANSCRIPT:\n{transcript}"
)


def _extract_json(text: str) -> dict:
    """Claude is instructed to return raw JSON, but strip fences defensively
    in case the model wraps it anyway."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    return json.loads(cleaned)


def summarize_transcript(transcript: str) -> dict:
    if not transcript.strip():
        return {"summary": "", "key_decisions": [], "action_items": []}

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(transcript=transcript)}
        ],
    )

    raw_text = "".join(block.text for block in response.content if block.type == "text")

    try:
        data = _extract_json(raw_text)
    except (json.JSONDecodeError, AttributeError):
        # Fall back to a safe shape if the model output couldn't be parsed,
        # so the API never 500s purely because of a formatting slip.
        data = {
            "summary": raw_text.strip(),
            "key_decisions": [],
            "action_items": [],
        }

    data.setdefault("summary", "")
    data.setdefault("key_decisions", [])
    data.setdefault("action_items", [])
    return data
