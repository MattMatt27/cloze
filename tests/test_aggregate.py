"""Unit tests for report/aggregate.py — derived metrics and render-time
co-occurrence selection. Pure functions, hand-built stats blocks."""
import pytest

from report.aggregate import derive_metrics, median, top_cooccurrences
from report.merge import empty_stats


def _stats(**overrides):
    stats = empty_stats()
    stats.update(overrides)
    return stats


def test_median_edge_cases():
    assert median([]) is None
    assert median([None, None]) is None
    assert median([3.0]) == 3.0
    assert median([1.0, 3.0]) == 2.0
    assert median([1.0, None, 3.0, 2.0]) == 2.0


def test_derive_metrics_on_empty():
    derived = derive_metrics(empty_stats())
    assert derived["conversations"] == 0
    assert derived["sentiment_mean"] is None
    assert derived["sentiment_stddev"] is None
    assert derived["median_user_messages"] is None
    assert derived["avg_messages_per_conversation"] == 0
    assert derived["voice_active_ratio"] == 0


def test_derive_metrics_sentiment_mean_and_stddev():
    # scores: 0.2, 0.4, 0.6 → mean 0.4, sample stddev 0.2
    stats = _stats(
        conversations=1,
        sentiment={"sum": 1.2, "sum_sq": 0.56, "count": 3,
                   "buckets": {"positive": 3, "neutral": 0, "negative": 0}},
    )
    derived = derive_metrics(stats)
    assert derived["sentiment_mean"] == pytest.approx(0.4)
    assert derived["sentiment_stddev"] == pytest.approx(0.2)
    assert derived["sentiment_percentages"]["positive"] == pytest.approx(100.0)


def test_derive_metrics_ratios():
    stats = _stats(
        conversations=2,
        messages={"user": 4, "assistant": 6},
        words={"user": 40, "assistant": 90},
        voice={"active": 6, "passive": 2},
        keywords={"categories": {}, "question_count": 2, "analyzed_texts": 4},
        per_conversation=[
            {"conversation_id": 1, "mean_sentiment": 0.5, "user_messages": 1,
             "user_words": 10, "duration_seconds": 100.0},
            {"conversation_id": 2, "mean_sentiment": None, "user_messages": 3,
             "user_words": 30, "duration_seconds": 300.0},
        ],
    )
    derived = derive_metrics(stats)
    assert derived["avg_messages_per_conversation"] == 5
    assert derived["avg_user_words_per_message"] == 10
    assert derived["avg_assistant_words_per_message"] == 15
    assert derived["voice_active_ratio"] == pytest.approx(75.0)
    assert derived["questions_per_user_message"] == pytest.approx(0.5)
    assert derived["median_user_messages"] == 2
    assert derived["median_sentiment"] == 0.5  # None entries excluded
    assert derived["median_duration_seconds"] == 200.0


def test_top_cooccurrences_threshold_and_ordering():
    stats = _stats(cooccurrence={
        "pairs": {"calm|breath": 5, "calm|walk": 1, "sleep|worry": 3},
        "words": {"calm": 6, "breath": 5, "walk": 1, "sleep": 3, "worry": 3},
        "sentences": 12,
    })
    result = top_cooccurrences(stats, min_count=2, top_pairs=10, top_words=3)
    assert [item["pair"] for item in result["pairs"]] == [
        ["calm", "breath"], ["sleep", "worry"],   # count-desc; walk filtered
    ]
    assert [w["word"] for w in result["top_words"]] == ["calm", "breath", "sleep"]
    assert result["total_unique_words"] == 5


def test_top_cooccurrences_none_when_unavailable():
    assert top_cooccurrences(empty_stats()) is None
