"""Extraction service tests — artifact correctness, idempotency, versioning,
and the extraction↔merge integration the scope engine will rely on."""
import json

import pytest

from llm_chat.models import AnalysisArtifact
from llm_chat.services import artifacts as artifacts_service
from llm_chat.services.artifacts import (
    ANALYZER_VERSION,
    conversations_missing_artifacts,
    extract_artifact,
)
from report.merge import merge

DAY1 = 1780000000.0  # fixed epochs → deterministic day buckets
DAY2 = DAY1 + 86400


@pytest.fixture(autouse=True)
def _fake_llm(monkeypatch):
    monkeypatch.setenv("CLOZE_FAKE_LLM", "1")


def test_extract_basic_stats(make_conversation):
    conversation = make_conversation([
        ("user", "I am feeling really happy today?", DAY1),
        ("assistant", "That is wonderful to hear from you.", DAY1 + 60),
        ("user", "Yes. Though maybe a bit anxious too.", DAY2),
    ])
    artifact = extract_artifact(conversation.id)
    stats = json.loads(artifact.artifact_data)

    assert artifact.status == "ready"
    assert artifact.analyzer_version == ANALYZER_VERSION
    assert stats["conversations"] == 1
    assert stats["messages"] == {"user": 2, "assistant": 1}
    assert stats["words"]["user"] == 6 + 7
    assert stats["first_message_at"] == DAY1
    assert stats["last_message_at"] == DAY2
    assert stats["duration_seconds"] == pytest.approx(DAY2 - DAY1)
    assert sum(stats["messages_by_day"].values()) == 3
    assert len(stats["messages_by_day"]) == 2  # spans two UTC days

    assert stats["sentiment"]["count"] == 2  # user messages only
    assert stats["keywords"]["question_count"] == 1
    assert stats["keywords"]["categories"]["positive"] >= 1  # "happy"
    assert stats["keywords"]["categories"]["uncertainty"] >= 1  # "maybe"

    entry = stats["per_conversation"][0]
    assert entry["conversation_id"] == conversation.id
    assert entry["user_messages"] == 2
    assert entry["mean_sentiment"] is not None

    assert artifact.ai_summary.startswith("[fake-llm]")
    assert "2 participant message" in artifact.ai_summary


def test_extract_empty_conversation(make_conversation):
    conversation = make_conversation([])
    artifact = extract_artifact(conversation.id)
    stats = json.loads(artifact.artifact_data)
    assert stats["messages"] == {}
    assert stats["first_message_at"] is None
    assert stats["cooccurrence"] is None
    assert artifact.ai_summary is None  # nothing to summarize


def test_extract_idempotent_and_force(make_conversation):
    conversation = make_conversation([("user", "Hello there.", DAY1)])
    first = extract_artifact(conversation.id)
    first_computed_at = first.computed_at

    again = extract_artifact(conversation.id)
    assert again.id == first.id
    assert again.computed_at == first_computed_at  # untouched, not recomputed

    forced = extract_artifact(conversation.id, force=True)
    assert forced.id == first.id  # upsert, not duplicate
    assert forced.computed_at >= first_computed_at
    assert AnalysisArtifact.query.filter_by(conversation_id=conversation.id).count() == 1


def test_version_bump_creates_new_row(make_conversation, monkeypatch):
    conversation = make_conversation([("user", "Hello there.", DAY1)])
    extract_artifact(conversation.id)

    monkeypatch.setattr(artifacts_service, "ANALYZER_VERSION", "2-test")
    assert conversations_missing_artifacts() == [conversation.id]  # old row is stale

    extract_artifact(conversation.id)
    rows = AnalysisArtifact.query.filter_by(conversation_id=conversation.id).all()
    assert sorted(row.analyzer_version for row in rows) == ["1", "2-test"]
    assert conversations_missing_artifacts() == []


def test_missing_conversation_raises(app):
    with pytest.raises(ValueError, match="not found"):
        extract_artifact(999999)


def test_missing_artifacts_listing(make_conversation):
    done = make_conversation([("user", "Covered.", DAY1)])
    pending = make_conversation([("user", "Not yet.", DAY1)])
    extract_artifact(done.id)
    assert conversations_missing_artifacts() == [pending.id]


def test_extracted_stats_merge_to_combined_totals(make_conversation):
    """Integration: merging two real artifacts equals hand-combined totals."""
    conv_a = make_conversation([
        ("user", "I feel great and happy.", DAY1),
        ("assistant", "Glad to hear it.", DAY1 + 30),
    ])
    conv_b = make_conversation([
        ("user", "Feeling sad and worried today?", DAY2),
    ])
    stats_a = json.loads(extract_artifact(conv_a.id).artifact_data)
    stats_b = json.loads(extract_artifact(conv_b.id).artifact_data)

    merged = merge(stats_a, stats_b)
    assert merged["conversations"] == 2
    assert merged["messages"] == {"user": 2, "assistant": 1}
    assert merged["sentiment"]["count"] == 2
    assert merged["sentiment"]["sum"] == pytest.approx(
        stats_a["sentiment"]["sum"] + stats_b["sentiment"]["sum"]
    )
    assert merged["first_message_at"] == DAY1
    assert merged["last_message_at"] == DAY2
    assert [e["conversation_id"] for e in merged["per_conversation"]] == sorted(
        [conv_a.id, conv_b.id]
    )
    assert merged["keywords"]["question_count"] == 1
