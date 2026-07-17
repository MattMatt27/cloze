"""Derived metrics over merged artifact stats. Pure — no DB, no Flask.

The merge layer (report/merge.py) stores only mergeable sufficient statistics;
anything presentational (means, ratios, medians) is derived here at render
time. Medians/percentiles come from the ``per_conversation`` list — the
carrier for scalars that don't fold from aggregates.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class GroupAggregate:
    """One natural child of a scope (a window, a flow, a participant…) with
    its own merged stats — the unit of trends and comparisons."""
    key: str
    label: str
    order: float
    stats: Dict[str, Any]


@dataclass
class AggregationContext:
    """Everything a component builder may consume. Assembled by the service
    layer (llm_chat/services/scope_engine.py); builders stay pure."""
    scope: str
    scope_id: int
    title: str
    stats: Dict[str, Any]                      # whole-scope merged stats
    derived: Dict[str, Any]                    # derive_metrics(stats)
    groups: List[GroupAggregate] = field(default_factory=list)  # time-ordered
    leaf_summaries: List[Tuple[int, str]] = field(default_factory=list)
    # per-conversation (conversation_id, ai_summary), scope-ordered
    group_summaries: Dict[str, List[Tuple[int, str]]] = field(default_factory=dict)
    # group.key -> that group's (conversation_id, summary) list
    meta: Dict[str, Any] = field(default_factory=dict)          # resolver meta
    synthesize: Optional[Callable[[List[str], str], Optional[str]]] = None
    # LLM seam injected by the service layer: (texts, level_label) -> summary


def median(values: List[float]) -> Optional[float]:
    cleaned = sorted(v for v in values if v is not None)
    if not cleaned:
        return None
    mid = len(cleaned) // 2
    if len(cleaned) % 2:
        return cleaned[mid]
    return (cleaned[mid - 1] + cleaned[mid]) / 2


def derive_metrics(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Render-ready numbers from one merged stats block."""
    messages = stats["messages"]
    words = stats["words"]
    total_messages = sum(messages.values())
    user_messages = messages.get("user", 0)
    assistant_messages = messages.get("assistant", 0)

    sentiment = stats["sentiment"]
    n = sentiment["count"]
    mean = (sentiment["sum"] / n) if n else None
    stddev = None
    if n > 1:
        variance = (sentiment["sum_sq"] - (sentiment["sum"] ** 2) / n) / (n - 1)
        stddev = math.sqrt(max(variance, 0.0))
    buckets = sentiment["buckets"]
    bucket_total = sum(buckets.values())

    voice = stats["voice"]
    voice_total = voice["active"] + voice["passive"]

    keywords = stats["keywords"]
    per_conversation = stats["per_conversation"]

    conversations = stats["conversations"]
    return {
        "conversations": conversations,
        "total_messages": total_messages,
        "user_messages": user_messages,
        "assistant_messages": assistant_messages,
        "avg_messages_per_conversation": (
            total_messages / conversations if conversations else 0
        ),
        "avg_user_words_per_message": (
            words.get("user", 0) / user_messages if user_messages else 0
        ),
        "avg_assistant_words_per_message": (
            words.get("assistant", 0) / assistant_messages if assistant_messages else 0
        ),
        "active_days": len(stats["messages_by_day"]),
        "first_message_at": stats["first_message_at"],
        "last_message_at": stats["last_message_at"],
        "total_duration_seconds": stats["duration_seconds"],
        "sentiment_mean": mean,
        "sentiment_stddev": stddev,
        "sentiment_percentages": {
            bucket: (count / bucket_total * 100 if bucket_total else 0)
            for bucket, count in buckets.items()
        },
        "voice_active_ratio": (voice["active"] / voice_total * 100) if voice_total else 0,
        "voice_passive_ratio": (voice["passive"] / voice_total * 100) if voice_total else 0,
        "questions_per_user_message": (
            keywords["question_count"] / user_messages if user_messages else 0
        ),
        "median_user_messages": median(
            [entry["user_messages"] for entry in per_conversation]
        ),
        "median_sentiment": median(
            [entry["mean_sentiment"] for entry in per_conversation]
        ),
        "median_duration_seconds": median(
            [entry["duration_seconds"] for entry in per_conversation]
        ),
    }


def top_cooccurrences(stats: Dict[str, Any], min_count: int = 2,
                      top_pairs: int = 20, top_words: int = 20) -> Optional[Dict[str, Any]]:
    """Threshold/top-N selection over *merged* pair counts — applied here, at
    render time, never at the leaf (leaf filtering would lose cross-
    conversation pairs; see design doc)."""
    cooccurrence = stats.get("cooccurrence")
    if not cooccurrence:
        return None
    pairs = [
        {"pair": key.split("|"), "count": count}
        for key, count in cooccurrence["pairs"].items()
        if count >= min_count
    ]
    pairs.sort(key=lambda item: (-item["count"], item["pair"]))
    words = sorted(cooccurrence["words"].items(), key=lambda kv: (-kv[1], kv[0]))
    return {
        "pairs": pairs[:top_pairs],
        "top_words": [{"word": word, "count": count} for word, count in words[:top_words]],
        "total_unique_words": len(cooccurrence["words"]),
        "sentences": cooccurrence["sentences"],
        "min_count": min_count,
    }
