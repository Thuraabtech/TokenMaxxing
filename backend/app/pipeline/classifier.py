"""Heuristic complexity classifier -- Phase 1/2 placeholder.

This is deliberately NOT the trained embedding classifier from the
blueprint's Phase 3. It exists so the routing pipeline is end-to-end
runnable from day one, while you collect the labeled (sub-task -> tier)
data needed to train the real thing. Swap this module's `classify()` for
an embedding + small classifier once you have ~300-500 labeled examples --
the router (router.py) doesn't need to change, only this function's body.
"""

import re

TIER_ORDER = ["low", "medium", "high"]
Tier = str  # "low" | "medium" | "high"

_HIGH_SIGNALS = re.compile(
    r"\b(compare|analy[sz]e|design|architect|evaluate|trade-?off|why|strategy|"
    r"optimi[sz]e|debug|refactor|prove|derive)\b",
    re.IGNORECASE,
)
_LOW_SIGNALS = re.compile(
    r"\b(what is|list|define|translate|format|extract|convert|summari[sz]e in one|"
    r"yes or no|true or false)\b",
    re.IGNORECASE,
)


def classify(subtask_text: str) -> tuple[Tier, float]:
    """Returns (tier, confidence in [0,1]). Confidence is the classifier's
    own certainty about the call, not model-answer confidence -- it's what
    the router uses to decide whether to escalate."""
    word_count = len(subtask_text.split())
    high_hits = len(_HIGH_SIGNALS.findall(subtask_text))
    low_hits = len(_LOW_SIGNALS.findall(subtask_text))

    if high_hits and high_hits >= low_hits:
        confidence = min(0.5 + 0.15 * high_hits, 0.9)
        return "high", confidence

    if low_hits and word_count < 40:
        confidence = min(0.5 + 0.15 * low_hits, 0.9)
        return "low", confidence

    if word_count > 60:
        return "high", 0.5

    if word_count < 15:
        return "low", 0.55

    return "medium", 0.6
