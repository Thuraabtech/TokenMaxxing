from typing import Literal

from pydantic import BaseModel

Tier = Literal["low", "medium", "high"]


class ChatRequest(BaseModel):
    message: str


class SubtaskResult(BaseModel):
    subtask_id: str
    text: str
    tier_used: Tier
    escalated_from: Tier | None = None
    confidence: float
    answer: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    saved_usd: float


class ChatResponse(BaseModel):
    answer: str
    subtasks: list[SubtaskResult]
    total_cost_usd: float
    total_saved_usd: float
    running_total_usd: float
    running_saved_usd: float
    retrieved_sources: list[str]
