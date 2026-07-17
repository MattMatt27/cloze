"""Mergeable sufficient statistics for report artifacts.

This module is pure — no DB, no Flask. It defines the artifact-stats schema
and the fold that turns per-conversation artifacts into aggregate stats for
any higher report scope (window, enrollment, participant, flow, account).

Design contract (tested in tests/test_merge_ops.py):
- ``merge(a, b)`` is associative and commutative,
- ``empty_stats()`` is its identity,
so aggregation order never affects results and scopes can be folded in any
grouping.

Merge rules by field:
- integer counters and count-dicts: element-wise sum
- ``first_message_at`` / ``last_message_at``: None-safe min / max
- ``sentiment``: sum / sum_sq / count / buckets all additive (mean and stddev
  are derived at render time, never stored)
- ``cooccurrence``: pair/word count-dicts additive; ``None`` (analyzer
  unavailable at extraction time) acts as identity so one degraded leaf does
  not poison an aggregate
- ``per_conversation``: concatenated and sorted by conversation_id — the
  order-insensitive carrier for scalars that do NOT fold from aggregates
  (medians/percentiles are computed over this list at render time; it stays
  small because it is one entry per conversation, not per message)
"""

from typing import Any, Dict, Iterable, Optional

SCHEMA_VERSION = 1


def empty_stats() -> Dict[str, Any]:
    """The merge identity: stats of zero conversations."""
    return {
        "schema_version": SCHEMA_VERSION,
        "conversations": 0,
        "messages": {},            # role -> count
        "words": {},               # role -> count
        "messages_by_day": {},     # "YYYY-MM-DD" -> count
        "first_message_at": None,  # epoch float
        "last_message_at": None,
        "duration_seconds": 0.0,   # sum of per-conversation durations
        "sentiment": {
            "sum": 0.0,
            "sum_sq": 0.0,
            "count": 0,
            "buckets": {"positive": 0, "neutral": 0, "negative": 0},
        },
        "voice": {"active": 0, "passive": 0},
        "keywords": {
            "categories": {},      # category -> count
            "question_count": 0,
            "analyzed_texts": 0,
        },
        "cooccurrence": None,      # {"pairs": {"a|b": n}, "words": {"w": n}, "sentences": n}
        "per_conversation": [],    # [{"conversation_id", "mean_sentiment", "user_messages",
                                   #   "user_words", "duration_seconds"}]
    }


def _sum_dicts(a: Dict[str, int], b: Dict[str, int]) -> Dict[str, int]:
    out = dict(a)
    for key, value in b.items():
        out[key] = out.get(key, 0) + value
    return out


def _min_optional(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)


def _max_optional(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)


def _merge_cooccurrence(a: Optional[Dict], b: Optional[Dict]) -> Optional[Dict]:
    if a is None:
        return b
    if b is None:
        return a
    return {
        "pairs": _sum_dicts(a.get("pairs", {}), b.get("pairs", {})),
        "words": _sum_dicts(a.get("words", {}), b.get("words", {})),
        "sentences": a.get("sentences", 0) + b.get("sentences", 0),
    }


def merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two stats blocks. Raises on schema mismatch rather than guessing."""
    if a.get("schema_version") != SCHEMA_VERSION or b.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"artifact schema mismatch: {a.get('schema_version')} vs {b.get('schema_version')} "
            f"(expected {SCHEMA_VERSION}); stale artifacts must be re-extracted"
        )

    sent_a, sent_b = a["sentiment"], b["sentiment"]
    kw_a, kw_b = a["keywords"], b["keywords"]

    per_conversation = sorted(
        list(a["per_conversation"]) + list(b["per_conversation"]),
        key=lambda entry: entry["conversation_id"],
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "conversations": a["conversations"] + b["conversations"],
        "messages": _sum_dicts(a["messages"], b["messages"]),
        "words": _sum_dicts(a["words"], b["words"]),
        "messages_by_day": _sum_dicts(a["messages_by_day"], b["messages_by_day"]),
        "first_message_at": _min_optional(a["first_message_at"], b["first_message_at"]),
        "last_message_at": _max_optional(a["last_message_at"], b["last_message_at"]),
        "duration_seconds": a["duration_seconds"] + b["duration_seconds"],
        "sentiment": {
            "sum": sent_a["sum"] + sent_b["sum"],
            "sum_sq": sent_a["sum_sq"] + sent_b["sum_sq"],
            "count": sent_a["count"] + sent_b["count"],
            "buckets": _sum_dicts(sent_a["buckets"], sent_b["buckets"]),
        },
        "voice": {
            "active": a["voice"]["active"] + b["voice"]["active"],
            "passive": a["voice"]["passive"] + b["voice"]["passive"],
        },
        "keywords": {
            "categories": _sum_dicts(kw_a["categories"], kw_b["categories"]),
            "question_count": kw_a["question_count"] + kw_b["question_count"],
            "analyzed_texts": kw_a["analyzed_texts"] + kw_b["analyzed_texts"],
        },
        "cooccurrence": _merge_cooccurrence(a["cooccurrence"], b["cooccurrence"]),
        "per_conversation": per_conversation,
    }


def merge_all(stats_blocks: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Fold any number of stats blocks; empty input yields ``empty_stats()``."""
    result = empty_stats()
    for block in stats_blocks:
        result = merge(result, block)
    return result
