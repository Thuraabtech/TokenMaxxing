from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_ROOT.parent / ".env", extra="ignore")

    aws_region: str = "us-east-1"

    model_id_low: str = "amazon.nova-micro-v1:0"
    model_id_medium: str = "REPLACE_WITH_CURRENT_CLAUDE_HAIKU_BEDROCK_ID"
    model_id_high: str = "REPLACE_WITH_CURRENT_CLAUDE_SONNET_BEDROCK_ID"
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    escalation_confidence_threshold: float = 0.55
    max_escalations: int = 2

    faiss_index_dir: str = "app/data/faiss_index"
    retrieval_top_k: int = 4

    # Output token ceilings per pipeline stage. The segmenter's ceiling matters
    # more than it looks -- too low and its JSON gets cut off mid-array for a
    # message with many distinct asks, which silently falls back to treating
    # the whole message as one sub-task (see segmenter.py's except clause).
    #
    # Per-tier ceilings for the answer call itself: low-tier sub-tasks are
    # almost always short (facts, arithmetic, short translations), while a
    # high-tier sub-task can legitimately be "design a full system architecture"
    # and needs real headroom. Confirmed against Bedrock's actual limits --
    # Nova Micro rejects anything above ~8-16k, Claude models accept 16k+.
    max_tokens_segment: int = 2048
    max_tokens_answer_low: int = 2048
    max_tokens_answer_medium: int = 4096
    max_tokens_answer_high: int = 16000
    max_tokens_assemble: int = 4096
    # Above this many sub-tasks, the assembler skips the LLM merge and just
    # concatenates labeled answers -- safer than asking a model to compress
    # many substantial, unrelated deliverables (code + a table + a story...)
    # into one merged voice without silently dropping content.
    assemble_merge_max_subtasks: int = 4

    price_low_in: float = 0.000035
    price_low_out: float = 0.00014
    price_medium_in: float = 0.0008
    price_medium_out: float = 0.004
    price_high_in: float = 0.003
    price_high_out: float = 0.015

    @property
    def model_ids(self) -> dict[str, str]:
        return {"low": self.model_id_low, "medium": self.model_id_medium, "high": self.model_id_high}

    @property
    def max_tokens_answer(self) -> dict[str, int]:
        return {
            "low": self.max_tokens_answer_low,
            "medium": self.max_tokens_answer_medium,
            "high": self.max_tokens_answer_high,
        }

    @property
    def prices(self) -> dict[str, dict[str, float]]:
        return {
            "low": {"in": self.price_low_in, "out": self.price_low_out},
            "medium": {"in": self.price_medium_in, "out": self.price_medium_out},
            "high": {"in": self.price_high_in, "out": self.price_high_out},
        }


settings = Settings()
