from app.pipeline.classifier import classify


def test_high_signal_keyword_routes_high():
    tier, confidence = classify("Compare these two database indexing strategies and their trade-offs")
    assert tier == "high"
    assert confidence > 0.5


def test_low_signal_short_lookup_routes_low():
    tier, _ = classify("What is the capital of France?")
    assert tier == "low"


def test_long_unsignaled_text_defaults_high_on_length():
    long_text = "explain " + ("context " * 60)
    tier, confidence = classify(long_text)
    assert tier in ("high", "medium")
    assert 0 <= confidence <= 1


def test_short_text_defaults_low():
    tier, _ = classify("Summarize this")
    assert tier == "low"
