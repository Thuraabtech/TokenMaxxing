import json
import re
import uuid

from app.bedrock_client import converse
from app.config import settings

SYSTEM_PROMPT = """You are a task segmenter. Split the user's message into independent \
sub-tasks needed to answer it fully.

- If the message contains an explicitly numbered or enumerated list of distinct \
requests (e.g. "1.", "2.", lettered items, section headers), treat EACH numbered item \
as its own sub-task. Do not bundle multiple numbered items into one -- they often need \
very different amounts of reasoning (a calculation and a system-design question are not \
the same sub-task just because they're in the same message).
- Otherwise, most single-question messages are one sub-task -- only split when the \
user is genuinely asking more than one distinct thing.

Respond with ONLY a JSON array, no prose, no markdown fences. Each element:
{"text": "<the sub-task, phrased as a standalone question or instruction>", \
"needs_retrieval": <true|false>}
"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    match = re.match(r"^```(?:json)?\s*(.*)\s*```$", text, re.DOTALL)
    return match.group(1) if match else text


def segment(message: str) -> list[dict]:
    raw, in_tok, out_tok = converse(
        settings.model_id_low, SYSTEM_PROMPT, message, max_tokens=settings.max_tokens_segment
    )
    try:
        parsed = json.loads(_strip_fences(raw))
        if not isinstance(parsed, list) or not parsed:
            raise ValueError("empty or non-list segmentation")
    except (json.JSONDecodeError, ValueError):
        # Segmenter is a low-tier model and can misbehave -- fall back to
        # treating the whole message as one sub-task rather than failing the request.
        parsed = [{"text": message, "needs_retrieval": True}]

    return [
        {"id": f"st-{uuid.uuid4().hex[:8]}", "text": item["text"], "needs_retrieval": item.get("needs_retrieval", True)}
        for item in parsed
    ], in_tok, out_tok
