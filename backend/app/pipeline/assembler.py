from app import cost_tracker
from app.bedrock_client import converse
from app.config import settings
from app.schemas import SubtaskResult

ASSEMBLE_SYSTEM_PROMPT = """You are merging answers to sub-tasks that were split from one \
user message back into a single, coherent reply. Do not repeat the sub-task labels -- \
write it as one direct answer to the original message.
"""


def _concatenate(results: list[SubtaskResult]) -> str:
    """Used instead of an LLM merge once there are enough sub-tasks that asking a model
    to compress them all into one voice risks silently dropping content (code, tables,
    a story, and a system design don't compress into a paragraph without losing something).
    """
    return "\n\n---\n\n".join(f"**{r.text}**\n\n{r.answer}" for r in results)


def assemble(original_message: str, results: list[SubtaskResult]) -> tuple[str, float, float]:
    if len(results) == 1:
        return results[0].answer, 0.0, 0.0

    if len(results) > settings.assemble_merge_max_subtasks:
        return _concatenate(results), 0.0, 0.0

    joined = "\n\n".join(f"[{r.subtask_id}] {r.text}\n-> {r.answer}" for r in results)
    user_message = f"Original message: {original_message}\n\nSub-task answers:\n{joined}"

    answer, in_tok, out_tok = converse(
        settings.model_id_medium, ASSEMBLE_SYSTEM_PROMPT, user_message, max_tokens=settings.max_tokens_assemble
    )
    cost, saved = cost_tracker.record("medium", in_tok, out_tok)
    return answer, cost, saved
