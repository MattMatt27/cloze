"""Scope resolver + aggregation engine tests.

Seeds a two-provider hierarchy so every scope has real structure to resolve,
including the FK window→flow link AND the legacy flow_name fallback, plus
cross-provider isolation checks.

Layout (provider1 unless noted):
  flow1 "Mindfulness" — phases: Week 1, Week 2
    alice enrolled:  w1 (Week 1, FK-linked, 2 convs)
                     w2 (Week 2, LEGACY name-linked, 1 conv)
    bob enrolled:    w3 (Week 1, FK-linked, 1 conv)   — never started Week 2
  standalone window: w4 for alice (no flow, 1 conv)
  free conversation: alice, window-less (1 conv)
  provider2: flow2 "Other Study", carol enrolled, w5 + 1 conv  — must never
             leak into provider1 scopes.
"""
import pytest
from conftest import DAY, T0

from llm_chat.extensions import db as _db
from llm_chat.models import AnalysisArtifact, ChatWindow
from llm_chat.services.scope_engine import generate_report_data
from llm_chat.services.scopes import (
    ScopeNotFoundError,
    UnknownScopeError,
    resolve_scope,
)
from report.registry_v2 import ALL_SCOPES, COMPONENTS


@pytest.fixture(autouse=True)
def _fake_llm(monkeypatch):
    monkeypatch.setenv("CLOZE_FAKE_LLM", "1")
    monkeypatch.delenv("REPORTS_WORKER_MODE", raising=False)


# --- registry matrix ----------------------------------------------------------

def test_registry_matrix_matches_design_doc():
    expected = {
        "descriptive_stats": ALL_SCOPES,
        "sentiment_analysis": ALL_SCOPES,
        "voice_analysis": ALL_SCOPES,
        "keyword_analysis": ALL_SCOPES,
        "cooccurrence": ALL_SCOPES - {"account"},
        "ai_summary": {"conversation"},
        "hierarchical_summary": ALL_SCOPES - {"conversation"},
        "trend_analysis": {"enrollment", "participant", "flow", "account"},
        "phase_comparison": {"enrollment", "participant"},
        "completion_analysis": {"flow", "account"},
        "engagement_overview": {"account"},
    }
    assert {k: set(c.scopes) for k, c in COMPONENTS.items()} == {
        k: set(v) for k, v in expected.items()
    }


# --- resolver -----------------------------------------------------------------

def test_resolve_enrollment_spans_fk_and_legacy_windows(study):
    selection = resolve_scope("enrollment", study.enr_alice.id)
    assert [g.label for g in selection.groups] == ["Week 1", "Week 2"]  # ordered
    assert selection.conversation_ids == [
        study.convs["a_w1_1"].id, study.convs["a_w1_2"].id, study.convs["a_w2_1"].id,
    ]
    assert selection.provider_id == study.provider1.id
    assert selection.patient_id == study.alice.id
    # bob's window in the same flow is NOT alice's
    assert study.convs["b_w3_1"].id not in selection.conversation_ids


def test_resolve_participant_groups_by_flow_with_buckets(study):
    selection = resolve_scope("participant", study.alice.id)
    labels = {g.label for g in selection.groups}
    assert labels == {"Mindfulness", "Unstructured windows", "Free conversations"}
    expected_ids = {study.convs[k].id
                    for k in ("a_w1_1", "a_w1_2", "a_w2_1", "a_w4_1", "a_free")}
    assert set(selection.conversation_ids) == expected_ids
    assert selection.provider_id == study.provider1.id


def test_resolve_flow_meta_counts(study):
    selection = resolve_scope("flow", study.flow1.id)
    assert [g.label for g in selection.groups] == ["alice", "bob"]  # by enrolled_at
    assert selection.meta["enrollment_count"] == 2
    assert selection.meta["started_count"] == 2
    # both alice and bob active in Week 1; only alice reached Week 2
    assert selection.meta["phase_participation"] == {"Week 1": 2, "Week 2": 1}


def test_resolve_account_isolated_per_provider(study):
    selection = resolve_scope("account", study.provider1.id)
    assert study.convs["c_w5_1"].id not in selection.conversation_ids  # provider2's
    labels = {g.label for g in selection.groups}
    assert labels == {"Mindfulness", "Standalone windows"}
    assert selection.meta["flow_count"] == 1
    assert selection.meta["patient_count"] == 2
    # free (window-less) conversations are patient-scope, not account-scope
    assert study.convs["a_free"].id not in selection.conversation_ids


def test_resolve_errors(study):
    with pytest.raises(UnknownScopeError):
        resolve_scope("galaxy", 1)
    with pytest.raises(ScopeNotFoundError):
        resolve_scope("flow", 999999)


# --- engine -------------------------------------------------------------------

def test_engine_window_scope_sections(study):
    data = generate_report_data("window", study.w1.id)
    assert data["conversation_count"] == 2
    sections = data["sections"]
    stats = sections["descriptive_stats"]
    assert stats["conversations"] == 2
    assert stats["user_messages"] == 2
    assert stats["assistant_messages"] == 1
    assert sections["sentiment_analysis"]["analyzed_messages"] == 2
    assert sections["keyword_analysis"]["question_count"] == 1  # "Maybe tired?"
    summary = sections["hierarchical_summary"]
    assert "[fake-llm] Synthesis" in summary["summary"]
    assert "ai_summary" not in sections  # leaf-only component
    assert "trend_analysis" not in sections  # not a window-scope component


def test_engine_auto_extracts_missing_artifacts(study):
    assert AnalysisArtifact.query.count() == 0
    progress = []
    generate_report_data("window", study.w1.id,
                         progress_cb=lambda c, t: progress.append((c, t)))
    assert AnalysisArtifact.query.count() == 2
    assert progress == [(1, 2), (2, 2)]


def test_engine_enrollment_trends_and_comparison(study):
    data = generate_report_data("enrollment", study.enr_alice.id)
    trend = data["sections"]["trend_analysis"]
    assert trend["group_kind"] == "window"
    assert [p["label"] for p in trend["sentiment"]] == ["Week 1", "Week 2"]
    # Week 1 is positive-toned, Week 2 negative — the trend must show the drop
    week1, week2 = (p["value"] for p in trend["sentiment"])
    assert week1 > week2

    comparison = data["sections"]["phase_comparison"]
    assert [row["label"] for row in comparison["rows"]] == ["Week 1", "Week 2"]
    assert comparison["rows"][0]["conversations"] == 2
    assert comparison["rows"][1]["conversations"] == 1

    summary = data["sections"]["hierarchical_summary"]
    assert len(summary["groups"]) == 2  # per-window syntheses feed the overall


def test_engine_flow_scope(study):
    data = generate_report_data("flow", study.flow1.id)
    assert data["conversation_count"] == 4  # alice 3 + bob 1
    completion = data["sections"]["completion_analysis"]
    assert completion["enrolled"] == 2 and completion["started"] == 2
    assert completion["phase_participation"] == {"Week 1": 2, "Week 2": 1}
    assert completion["inactive"] == []


def test_engine_account_scope(study):
    data = generate_report_data("account", study.provider1.id)
    sections = data["sections"]
    assert "cooccurrence" not in sections  # excluded at account scope
    overview = sections["engagement_overview"]
    assert {row["label"] for row in overview["rows"]} == {
        "Mindfulness", "Standalone windows"
    }
    mindfulness = next(r for r in overview["rows"] if r["label"] == "Mindfulness")
    assert mindfulness["conversations"] == 4
    completion = sections["completion_analysis"]
    assert completion["by_flow"][0]["name"] == "Mindfulness"


def test_engine_conversation_scope_leaf_summary(study):
    data = generate_report_data("conversation", study.convs["a_w1_1"].id)
    assert data["conversation_count"] == 1
    assert data["sections"]["ai_summary"]["summary"].startswith("[fake-llm]")
    assert "hierarchical_summary" not in data["sections"]


def test_engine_component_restriction(study):
    data = generate_report_data("window", study.w1.id,
                                components=["descriptive_stats"])
    assert set(data["sections"]) == {"descriptive_stats"}


def test_engine_empty_scope(study):
    """A window with no conversations renders the empty shell, not an error."""
    empty_window = ChatWindow(patient_id=study.bob.id,
                              provider_id=study.provider1.id,
                              title="Untouched", start_date=T0, end_date=T0 + DAY)
    _db.session.add(empty_window)
    _db.session.commit()
    data = generate_report_data("window", empty_window.id)
    assert data["conversation_count"] == 0
    assert data["sections"]["descriptive_stats"]["conversations"] == 0
    assert "sentiment_analysis" not in data["sections"]  # nothing analyzed
    assert "hierarchical_summary" not in data["sections"]
