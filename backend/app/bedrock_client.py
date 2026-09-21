import boto3
from botocore.config import Config

from app.config import settings

_client = None

# boto3's default read timeout (60s) is tuned for typical API calls, not for
# waiting on a model to generate up to 8192 output tokens -- a long high-tier
# generation can genuinely take longer than that and would otherwise surface
# as a ReadTimeoutError with an empty response body.
_BEDROCK_CONFIG = Config(read_timeout=300, connect_timeout=10, retries={"max_attempts": 2})


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name=settings.aws_region, config=_BEDROCK_CONFIG)
    return _client


def converse(model_id: str, system_prompt: str, user_message: str, max_tokens: int = 1024, temperature: float = 0.2):
    """Thin wrapper around Bedrock's Converse API. Returns (text, input_tokens, output_tokens)."""
    client = _get_client()
    response = client.converse(
        modelId=model_id,
        system=[{"text": system_prompt}] if system_prompt else [],
        messages=[{"role": "user", "content": [{"text": user_message}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
    text = response["output"]["message"]["content"][0]["text"]
    usage = response.get("usage", {})
    return text, usage.get("inputTokens", 0), usage.get("outputTokens", 0)
