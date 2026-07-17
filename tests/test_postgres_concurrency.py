"""Postgres-only queue invariants — the one behavior SQLite cannot test.

Runs only when TEST_POSTGRES_URL is set (e.g.
``postgresql://postgres:postgres@localhost:5432/cloze_test``). Locally either
``docker run --rm -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=cloze_test -p 5432:5432 postgres:16``
or a throwaway Homebrew cluster (``initdb`` + ``pg_ctl`` on a spare port),
then ``TEST_POSTGRES_URL=... pytest -m postgres``. A CI job for these exists
in .github/workflows/ci.yml, which is deliberately untracked until the team
moves off manual-only deploys — run this lane before merging queue changes.

The invariant: FOR UPDATE SKIP LOCKED claims give each concurrent claimer a
distinct job — never double-execution, never a lost job.
"""
import os
import threading

import pytest

pytestmark = pytest.mark.postgres

POSTGRES_URL = os.environ.get("TEST_POSTGRES_URL")

if not POSTGRES_URL:
    pytest.skip("TEST_POSTGRES_URL not set", allow_module_level=True)


@pytest.fixture
def pg_app(monkeypatch):
    """An app bound to the test Postgres instead of the default sqlite."""
    monkeypatch.setenv("DATABASE_URL", POSTGRES_URL)
    monkeypatch.setenv("CLOZE_FAKE_LLM", "1")
    monkeypatch.delenv("REPORTS_WORKER_MODE", raising=False)

    from llm_chat import create_app
    from llm_chat.extensions import db as _db

    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        _db.drop_all()
        _db.create_all()
    yield app
    with app.app_context():
        _db.session.remove()
        _db.drop_all()


def test_dialect_is_postgres(pg_app):
    from llm_chat.extensions import db as _db
    with pg_app.app_context():
        assert _db.session.get_bind().dialect.name == "postgresql"


def test_concurrent_claims_are_disjoint_and_complete(pg_app):
    """Two claimers racing over one queue: every job claimed exactly once."""
    from llm_chat.extensions import db as _db
    from llm_chat.services.report_jobs import claim_next_job, enqueue

    n_jobs = 24
    with pg_app.app_context():
        job_ids = [enqueue("backfill").id for _ in range(n_jobs)]

    barrier = threading.Barrier(2)
    claimed_by_thread = {0: [], 1: []}
    errors = []

    def claimer(thread_index):
        try:
            barrier.wait(timeout=5)
            # Each thread gets its own app context → its own scoped session
            # → its own DB connection: a genuine two-consumer race.
            with pg_app.app_context():
                while True:
                    job = claim_next_job()
                    if job is None:
                        break
                    claimed_by_thread[thread_index].append(job.id)
                _db.session.remove()
        except Exception as exc:  # surface thread failures in the main assert
            errors.append(exc)

    threads = [threading.Thread(target=claimer, args=(i,)) for i in (0, 1)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors, errors
    claimed_a, claimed_b = set(claimed_by_thread[0]), set(claimed_by_thread[1])
    assert claimed_a.isdisjoint(claimed_b), "a job was claimed by both workers"
    assert claimed_a | claimed_b == set(job_ids), "jobs lost during claiming"

    with pg_app.app_context():
        from llm_chat.models import ReportJob
        assert ReportJob.query.filter_by(status="running").count() == n_jobs
        # attempts == 1 everywhere: claimed once, by exactly one worker
        assert {j.attempts for j in ReportJob.query.all()} == {1}


def test_reclaimed_jobs_are_claimable_again(pg_app):
    """Lease expiry → reclaim → a new claimer picks the job up exactly once."""
    from llm_chat.services.report_jobs import (
        claim_next_job, enqueue, reclaim_stale_jobs,
    )

    with pg_app.app_context():
        job = enqueue("backfill")
        claimed = claim_next_job()
        assert claimed.id == job.id
        claimed.heartbeat_at = 0.0  # ancient — lease long expired

        requeued, failed = reclaim_stale_jobs()
        assert requeued == [job.id] and failed == []

        reclaimed = claim_next_job()
        assert reclaimed.id == job.id
        assert reclaimed.attempts == 2
        assert claim_next_job() is None
