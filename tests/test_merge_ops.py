"""Property tests for report/merge.py — the aggregation algebra.

The whole multi-scope report design rests on merge being an associative,
commutative monoid with empty_stats() as identity: any scope can then fold
its artifacts in any grouping/order and get identical results.
"""
import random

import pytest

from report.merge import SCHEMA_VERSION, empty_stats, merge, merge_all


def _random_stats(rng, conversation_id):
    """A plausible single-conversation stats block."""
    n_user = rng.randint(0, 40)
    n_assistant = rng.randint(0, 40)
    scores = [rng.uniform(-1, 1) for _ in range(n_user)]
    day = f"2026-07-{rng.randint(1, 28):02d}"
    first = rng.uniform(1e9, 2e9) if (n_user + n_assistant) else None
    coocc = None
    if rng.random() < 0.7:
        coocc = {
            "pairs": {f"w{rng.randint(0, 5)}|w{rng.randint(6, 9)}": rng.randint(1, 4)
                      for _ in range(rng.randint(0, 6))},
            "words": {f"w{rng.randint(0, 9)}": rng.randint(1, 5)
                      for _ in range(rng.randint(0, 6))},
            "sentences": rng.randint(0, 30),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "conversations": 1,
        "messages": {"user": n_user, "assistant": n_assistant},
        "words": {"user": n_user * 7, "assistant": n_assistant * 11},
        "messages_by_day": {day: n_user + n_assistant},
        "first_message_at": first,
        "last_message_at": (first + rng.uniform(0, 5000)) if first is not None else None,
        "duration_seconds": rng.uniform(0, 5000),
        "sentiment": {
            "sum": sum(scores),
            "sum_sq": sum(s * s for s in scores),
            "count": len(scores),
            "buckets": {
                "positive": sum(1 for s in scores if s > 0.1),
                "neutral": sum(1 for s in scores if -0.1 <= s <= 0.1),
                "negative": sum(1 for s in scores if s < -0.1),
            },
        },
        "voice": {"active": rng.randint(0, 30), "passive": rng.randint(0, 10)},
        "keywords": {
            "categories": {"positive": rng.randint(0, 5), "negative": rng.randint(0, 5),
                           "uncertainty": rng.randint(0, 5)},
            "question_count": rng.randint(0, 10),
            "analyzed_texts": n_user,
        },
        "cooccurrence": coocc,
        "per_conversation": [{
            "conversation_id": conversation_id,
            "mean_sentiment": (sum(scores) / len(scores)) if scores else None,
            "user_messages": n_user,
            "user_words": n_user * 7,
            "duration_seconds": 0.0,
        }],
    }


def _blocks(seed, n):
    rng = random.Random(seed)
    return [_random_stats(rng, conversation_id=i + 1) for i in range(n)]


def _approx_equal(a, b, path=""):
    """Deep compare with float tolerance (merge order changes float rounding)."""
    if isinstance(a, float) or isinstance(b, float):
        assert a == pytest.approx(b), path
    elif isinstance(a, dict):
        assert isinstance(b, dict) and set(a) == set(b), path
        for key in a:
            _approx_equal(a[key], b[key], f"{path}.{key}")
    elif isinstance(a, list):
        assert isinstance(b, list) and len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b)):
            _approx_equal(x, y, f"{path}[{i}]")
    else:
        assert a == b, path


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_merge_associative(seed):
    a, b, c = _blocks(seed, 3)
    _approx_equal(merge(merge(a, b), c), merge(a, merge(b, c)))


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_merge_commutative(seed):
    a, b = _blocks(seed, 2)
    _approx_equal(merge(a, b), merge(b, a))


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_empty_is_identity(seed):
    (a,) = _blocks(seed, 1)
    _approx_equal(merge(a, empty_stats()), a)
    _approx_equal(merge(empty_stats(), a), a)


@pytest.mark.parametrize("seed", [0, 7, 42])
def test_fold_order_and_grouping_invariant(seed):
    """The property the scope engine relies on: any grouping, any order."""
    blocks = _blocks(seed, 8)
    sequential = merge_all(blocks)

    shuffled = list(blocks)
    random.Random(seed + 99).shuffle(shuffled)
    halves = merge(merge_all(shuffled[:3]), merge_all(shuffled[3:]))

    _approx_equal(sequential, halves)


def test_merge_all_empty_input():
    assert merge_all([]) == empty_stats()


def test_degraded_cooccurrence_is_identity():
    """A leaf where the analyzer was unavailable must not poison aggregates."""
    a, b = _blocks(3, 2)
    a["cooccurrence"] = None
    merged = merge(a, b)
    assert merged["cooccurrence"] == b["cooccurrence"]
    b["cooccurrence"] = None
    assert merge(a, b)["cooccurrence"] is None


def test_schema_mismatch_raises():
    a, b = _blocks(5, 2)
    b["schema_version"] = SCHEMA_VERSION + 1
    with pytest.raises(ValueError, match="schema mismatch"):
        merge(a, b)


def test_per_conversation_sorted_and_complete():
    blocks = _blocks(11, 5)
    merged = merge_all(reversed(blocks))
    ids = [entry["conversation_id"] for entry in merged["per_conversation"]]
    assert ids == sorted(ids) == [1, 2, 3, 4, 5]
