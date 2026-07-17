"""kind='report' jobs: scope target → engine → persisted Report row.

One Report row per (scope, target, report_type='v2'), updated in place on
regeneration — the invariant behind the UI's ready/stale chip model."""
import json

import pytest

from llm_chat.models import Report, ReportJob
from llm_chat.services.report_jobs import SCOPE_FK, enqueue, enqueue_report, run_once


@pytest.fixture(autouse=True)
def _fake_llm(monkeypatch):
    monkeypatch.setenv("CLOZE_FAKE_LLM", "1")
    monkeypatch.delenv("REPORTS_WORKER_MODE", raising=False)


def _run_report(scope, scope_id):
    job = enqueue_report(scope, scope_id)
    executed = run_once()
    assert executed.id == job.id
    return executed


def test_window_report_persisted(study):
    executed = _run_report("window", study.w1.id)
    assert executed.status == "done", executed.error

    report = Report.query.filter_by(scope="window", window_id=study.w1.id,
                                    report_type="v2").one()
    assert executed.report_id == report.id
    assert report.provider_id == study.provider1.id
    assert report.patient_id == study.alice.id
    assert report.analyzer_version == "1"
    data = json.loads(report.report_data)
    assert data["scope"] == "window"
    assert data["conversation_count"] == 2
    assert "descriptive_stats" in data["sections"]


def test_regenerate_updates_in_place(study):
    first = _run_report("window", study.w1.id)
    second = _run_report("window", study.w1.id)
    assert first.status == second.status == "done"

    reports = Report.query.filter_by(scope="window", window_id=study.w1.id).all()
    assert len(reports) == 1  # upsert, never a duplicate
    assert second.report_id == first.report_id


def test_each_scope_targets_its_fk_column(study):
    targets = {
        "conversation": study.convs["a_w1_1"].id,
        "window": study.w1.id,
        "enrollment": study.enr_alice.id,
        "participant": study.alice.id,
        "flow": study.flow1.id,
        "account": study.provider1.id,
    }
    for scope, scope_id in targets.items():
        executed = _run_report(scope, scope_id)
        assert executed.status == "done", f"{scope}: {executed.error}"
        report = Report.query.filter_by(
            scope=scope, report_type="v2", **{SCOPE_FK[scope]: scope_id}
        ).one()
        assert report.provider_id == study.provider1.id, scope

    assert Report.query.filter_by(report_type="v2").count() == len(targets)
    # flow/account scope rows have no single patient
    assert Report.query.filter_by(scope="flow").one().patient_id is None
    assert Report.query.filter_by(scope="account").one().patient_id is None


def test_windowless_conversation_gets_provider_via_link(study):
    """Free-chat conversation: ownership falls back to the ProviderPatient link."""
    executed = _run_report("conversation", study.convs["a_free"].id)
    assert executed.status == "done", executed.error
    report = Report.query.filter_by(scope="conversation",
                                    conversation_id=study.convs["a_free"].id).one()
    assert report.provider_id == study.provider1.id
    assert report.window_id is None


def test_report_job_progress_tracks_extraction(study):
    executed = _run_report("enrollment", study.enr_alice.id)
    assert executed.status == "done"
    assert executed.progress_total == 3  # alice's three flow conversations
    assert executed.progress_current == 3


def test_report_job_without_target_fails(app):
    enqueue("report", scope="window")  # no window_id set
    executed = run_once()
    assert executed.status == "failed"
    assert "no target id" in executed.error


def test_report_job_unknown_scope_rejected_at_enqueue(app):
    with pytest.raises(ValueError, match="unknown scope"):
        enqueue_report("galaxy", 1)


def test_report_job_missing_entity_fails_cleanly(app):
    enqueue_report("flow", 999999)
    executed = run_once()
    assert executed.status == "failed"
    assert "not found" in executed.error
    assert Report.query.count() == 0  # row only written on success


def test_legacy_rows_read_as_window_scope(study):
    legacy = Report(window_id=study.w1.id, patient_id=study.alice.id,
                    provider_id=study.provider1.id, report_type="summary",
                    report_data="{}")
    from llm_chat.extensions import db as _db
    _db.session.add(legacy)
    _db.session.commit()
    assert legacy.scope is None
    assert legacy.effective_scope == "window"
    assert legacy.to_dict()["scope"] == "window"


def test_v2_and_legacy_coexist_on_same_window(study):
    from llm_chat.extensions import db as _db
    legacy = Report(window_id=study.w1.id, patient_id=study.alice.id,
                    provider_id=study.provider1.id, report_type="summary",
                    report_data="{}")
    _db.session.add(legacy)
    _db.session.commit()

    executed = _run_report("window", study.w1.id)
    assert executed.status == "done"
    assert Report.query.filter_by(window_id=study.w1.id).count() == 2  # legacy + v2
    assert ReportJob.query.filter_by(status="done").count() == 1