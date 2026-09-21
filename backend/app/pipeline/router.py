from app import cost_tracker
from app.bedrock_client import converse
from app.config import settings
from app.pipeline.classifier import TIER_ORDER, classify
from app.schemas import SubtaskResult
from app.toon_codec import encode_table

ANSWER_SYSTEM_PROMPT = """Answer the user's sub-task directly and concisely. \
If TOON-encoded context rows are provided below, use them as ground truth; \
if they don't contain the answer, say so rather than guessing.

If the sub-task has many distinct required parts (e.g. "design a system covering \
these 10 components"), make sure every part gets a complete treatment within your \
response -- prioritize covering all of them clearly over exhaustive depth on the \
first few. An answer that finishes covering everything concisely is better than one \
that runs out of room partway through.
"""


def _build_user_message(subtask_text: str, context_rows: list[dict]) -> str:
    if not context_rows:
        return subtask_text
    toon_context = encode_table(context_rows)
    return f"Context:\n{toon_context}\n\nSub-task: {subtask_text}"


def _next_tier(tier: str) -> str | None:
    idx = TIER_ORDER.index(tier)
    return TIER_ORDER[idx + 1] if idx + 1 < len(TIER_ORDER) else None


def route(subtask: dict, context_rows: list[dict]) -> SubtaskResult:
    tier, confidence = classify(subtask["text"])
    original_tier = tier
    user_message = _build_user_message(subtask["text"], context_rows)

    escalations = 0
    while True:
        model_id = settings.model_ids[tier]
        answer, in_tok, out_tok = converse(
            model_id, ANSWER_SYSTEM_PROMPT, user_message, max_tokens=settings.max_tokens_answer[tier]
        )
        cost, saved = cost_tracker.record(tier, in_tok, out_tok)

        should_escalate = (
            confidence < settings.escalation_confidence_threshold
            and escalations < settings.max_escalations
            and _next_tier(tier) is not None
        )
        if not should_escalate:
            break
        tier = _next_tier(tier)
        escalations += 1

    return SubtaskResult(
        subtask_id=subtask["id"],
        text=subtask["text"],
        tier_used=tier,
        escalated_from=original_tier if tier != original_tier else None,
        confidence=confidence,
        answer=answer,
        input_tokens=in_tok,
        output_tokens=out_tok,
        cost_usd=round(cost, 6),
        saved_usd=round(saved, 6),
    )
