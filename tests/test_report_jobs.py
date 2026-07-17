"""Job queue tests — full lifecycle, lease reclaim, idempotency, failure
capture, eager mode. All deterministic: no threads, no sleeps; failure modes
are simulated by hand-setting state, never by killing processes."""
import pytest

from llm_chat.models import AnalysisArtifact
from llm_chat.services.artifacts import extract_artifact
from llm_chat.services.report_jobs import (
    MAX_ATTEMPTS,
    claim_next_job,
    enqueue,
    execute_job,
    reclaim_stale_jobs,
    run_once,
)

DAY1 = 1780000000.0


@pytest.fixture(autouse=True)
def _fake_llm(monkeypatch):
    monkeypatch.setenv("CLOZE_FAKE_LLM", "1")
    monkeypatch.delenv("REPORTS_WORKER_MODE", raising=False)


def test_extract_job_lifecycle(make_conversation):
    conversation = make_conversation([("user", "Hello there.", DAY1)])
    job = enqueue("extract", conversation_id=conversation.id)
    assert job.status == "queued"
    assert job.started_at is None

    executed = run_once()
    assert executed.id == job.id
    assert executed.status == "done"
    assert executed.attempts == 1
    assert executed.progress_current == executed.progress_total == 1
    assert executed.started_at is not None and executed.finished_at is not None
    assert AnalysisArtifact.query.filter_by(conversation_id=conversation.id).count() == 1


def test_run_once_empty_queue(app):
    assert run_once() is None


def test_claim_is_fifo(make_conversation):
    conv_a = make_conversation([("user", "First.", DAY1)])
    conv_b = make_conversation([("user", "Second.", DAY1)])
    job_a = enqueue("extract", conversation_id=conv_a.id)
    job_b = enqueue("extract", conversation_id=conv_b.id)
    # Deterministic ordering even within one clock tick
    job_a.created_at, job_b.created_at = DAY1, DAY1 + 1

    assert claim_next_job().id == job_a.id
    assert claim_next_job().id == job_b.id
    assert claim_next_job() is None  # both now running


def test_eager_mode_executes_inline(make_conversation, monkeypatch):
    monkeypatch.setenv("REPORTS_WORKER_MODE", "eager")
    conversation = make_conversation([("user", "Hello there.", DAY1)])
    job = enqueue("extract", conversation_id=conversation.id)
    assert job.status == "done"
    assert AnalysisArtifact.query.filter_by(conversation_id=conversation.id).count() == 1


def test_failure_captured_on_row(app):
    enqueue("extract", conversation_id=999999)  # nonexistent conversation
    executed = run_once()
    assert executed.status == "failed"
    assert "not found" in executed.error
    assert executed.finished_at is not None


def test_unknown_kind_fails_cleanly(app):
    enqueue("frobnicate")
    executed = run_once()
    assert executed.status == "failed"
    assert "unknown job kind" in executed.error


def test_lease_reclaim_requeues_stale(make_conversation, monkeypatch):
    conversation = make_conversation([("user", "Hello there.", DAY1)])
    job = enqueue("extract", conversation_id=conversation.id)
    claimed = claim_next_job()
    assert claimed.id == job.id and claimed.status == "running"

    # Simulate a dead worker: heartbeat far in the past.
    claimed.heartbeat_at = DAY1
    requeued, failed = reclaim_stale_jobs()
    assert requeued == [job.id] and failed == []
    assert claimed.status == "queued" and claimed.heartbeat_at is None
    assert claimed.attempts == 1  # attempts preserved across reclaim

    # The reclaimed job completes on the next iteration.
    assert run_once().status == "done"


def test_lease_reclaim_gives_up_after_max_attempts(make_conversation):
    conversation = make_conversation([("user", "Hello there.", DAY1)])
    job = enqueue("extract", conversation_id=conversation.id)
    claimed = claim_next_job()
    claimed.attempts = MAX_ATTEMPTS
    claimed.heartbeat_at = DAY1  # stale

    requeued, failed = reclaim_stale_jobs()
    assert requeued == [] and failed == [job.id]
    assert claimed.status == "failed"
    assert "giving up" in claimed.error


def test_fresh_running_job_not_reclaimed(make_conversation):
    conversation = make_conversation([("user", "Hello there.", DAY1)])
    enqueue("extract", conversation_id=conversation.id)
    claimed = claim_next_job()  # heartbeat = now
    requeued, failed = reclaim_stale_jobs()
    assert requeued == [] and failed == []
    assert claimed.status == "running"


def test_execute_twice_is_idempotent(make_conversation):
    """Lease semantics allow a job to run again after a crash mid-execution;
    handlers must upsert, not duplicate."""
    conversation = make_conversation([("user", "Hello there.", DAY1)])
    job = enqueue("extract", conversation_id=conversation.id)
    execute_job(job)
    execute_job(job)
    assert AnalysisArtifact.query.filter_by(conversation_id=conversation.id).count() == 1


def test_backfill_extracts_missing_only(make_conversation):
    conv_a = make_conversation([("user", "Already done.", DAY1)])
    conv_b = make_conversation([("user", "Pending one.", DAY1)])
    conv_c = make_conversation([("user", "Pending two.", DAY1)])
    extract_artifact(conv_a.id)

    job = enqueue("backfill")
    executed = run_once()
    assert executed.status == "done"
    assert executed.progress_current == executed.progress_total == 2
    assert AnalysisArtifact.query.count() == 3
    for conv in (conv_a, conv_b, conv_c):
        assert AnalysisArtifact.query.filter_by(conversation_id=conv.id).count() == 1
    assert job.id == executed.id


def test_backfill_empty_is_done(app):
    enqueue("backfill")
    executed = run_once()
    assert executed.status == "done"
    assert executed.progress_total == 0
