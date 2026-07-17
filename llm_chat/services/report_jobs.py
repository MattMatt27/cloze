"""Report-v2 job queue — enqueue / claim / lease / execute.

The queue is the database (``report_jobs``); the consumer is the dedicated
worker process (``flask reports-worker``). Design: .docs/roadmap/report-system-v2.md.

Deliberate properties:
- **Claims** use ``FOR UPDATE SKIP LOCKED`` on Postgres so any number of
  workers can consume concurrently without double-execution. On SQLite (local
  dev, single worker by definition) a plain transaction suffices — guarded by
  dialect, each path tested on its own dialect.
- **Leases, not locks:** a running job proves liveness via ``heartbeat_at``.
  Stale running jobs are reclaimed to ``queued`` (or failed after
  ``MAX_ATTEMPTS``), so a worker crash/OOM loses nothing. Handlers must
  therefore be idempotent — artifact extraction upserts, report rows are
  written last.
- **Eager mode** (``REPORTS_WORKER_MODE=eager``): enqueue executes the job
  inline — one-terminal local dev and simple tests. Production leaves the
  variable unset and runs the worker process.

Everything here is callable synchronously (``run_once``) — the worker loop is
a thin wrapper, and tests never need threads or sleeps.
"""

import json
import os
import time
import traceback

from sqlalchemy import text

from ..extensions import db
from ..models import Report, ReportJob
from .artifacts import conversations_missing_artifacts, extract_artifact

STALE_AFTER_SECONDS = 300  # running job with a heartbeat older than this is reclaimable
MAX_ATTEMPTS = 3           # reclaims beyond this fail the job instead

# scope → the ReportJob/Report FK column that carries the target id
SCOPE_FK = {
    "conversation": "conversation_id",
    "window": "window_id",
    "enrollment": "flow_enrollment_id",
    "participant": "patient_id",
    "flow": "flow_id",
    "account": "provider_id",
}


def _now():
    return time.time()


# --- enqueue ------------------------------------------------------------------

def enqueue(kind, *, scope=None, conversation_id=None, window_id=None,
            flow_enrollment_id=None, patient_id=None, flow_id=None,
            provider_id=None, payload=None, requested_by=None):
    """Create a queued job. In eager mode, execute it inline before returning."""
    job = ReportJob(
        kind=kind,
        scope=scope,
        conversation_id=conversation_id,
        window_id=window_id,
        flow_enrollment_id=flow_enrollment_id,
        patient_id=patient_id,
        flow_id=flow_id,
        provider_id=provider_id,
        payload=json.dumps(payload) if payload else None,
        requested_by=requested_by,
    )
    db.session.add(job)
    db.session.commit()

    if os.environ.get("REPORTS_WORKER_MODE") == "eager":
        _mark_running(job)
        execute_job(job)
    return job


def enqueue_report(scope, scope_id, *, requested_by=None, payload=None):
    """Enqueue a scope-report generation job, targeting via the right FK."""
    if scope not in SCOPE_FK:
        raise ValueError(f"unknown scope {scope!r}; expected one of {sorted(SCOPE_FK)}")
    return enqueue("report", scope=scope, requested_by=requested_by,
                   payload=payload, **{SCOPE_FK[scope]: scope_id})


def _mark_running(job):
    now = _now()
    job.status = "running"
    job.started_at = now
    job.heartbeat_at = now
    job.attempts += 1
    db.session.commit()


# --- claim / lease ------------------------------------------------------------

def claim_next_job():
    """Atomically claim the oldest queued job, or return None.

    Postgres: SELECT ... FOR UPDATE SKIP LOCKED and the status flip commit as
    one transaction, so concurrent claimers each get distinct jobs.
    """
    if db.session.get_bind().dialect.name == "postgresql":
        row = db.session.execute(text(
            "SELECT id FROM report_jobs WHERE status = 'queued' "
            "ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED"
        )).first()
        if row is None:
            db.session.rollback()
            return None
        job = db.session.get(ReportJob, row[0])
    else:
        job = (ReportJob.query.filter_by(status="queued")
               .order_by(ReportJob.created_at).first())
        if job is None:
            return None
    _mark_running(job)
    return job


def heartbeat(job, current=None, total=None):
    """Prove liveness and optionally update progress. Called by handlers."""
    job.heartbeat_at = _now()
    if current is not None:
        job.progress_current = current
    if total is not None:
        job.progress_total = total
    db.session.commit()


def reclaim_stale_jobs():
    """Requeue running jobs whose lease expired; fail those out of attempts.

    Returns (requeued_ids, failed_ids)."""
    cutoff = _now() - STALE_AFTER_SECONDS
    stale = ReportJob.query.filter(
        ReportJob.status == "running", ReportJob.heartbeat_at < cutoff
    ).all()
    requeued, failed = [], []
    for job in stale:
        if job.attempts >= MAX_ATTEMPTS:
            job.status = "failed"
            job.error = f"lease expired after {job.attempts} attempts; giving up"
            job.finished_at = _now()
            failed.append(job.id)
        else:
            job.status = "queued"
            job.heartbeat_at = None
            requeued.append(job.id)
    if stale:
        db.session.commit()
    return requeued, failed


# --- execution ----------------------------------------------------------------

def _job_payload(job):
    return json.loads(job.payload) if job.payload else {}


def _handle_extract(job):
    payload = _job_payload(job)
    heartbeat(job, current=0, total=1)
    extract_artifact(job.conversation_id, force=payload.get("force", False))
    heartbeat(job, current=1, total=1)


def _handle_backfill(job):
    payload = _job_payload(job)
    throttle = float(payload.get("throttle_seconds", 0))
    pending = conversations_missing_artifacts()
    heartbeat(job, current=0, total=len(pending))
    for index, conversation_id in enumerate(pending, start=1):
        extract_artifact(conversation_id)
        heartbeat(job, current=index, total=len(pending))
        if throttle:
            time.sleep(throttle)


def _handle_report(job):
    """Generate a scope report and upsert THE Report row for that scope target.

    One row per (scope, target, report_type='v2') — regeneration updates in
    place, which is what makes the UI's ready/stale chip model coherent.
    The row is written only on success (lease re-runs regenerate wholesale)."""
    from .scope_engine import generate_report_data  # deferred: pulls analyzers

    scope = job.scope
    if scope not in SCOPE_FK:
        raise ValueError(f"report job {job.id} has unknown scope {scope!r}")
    scope_id = getattr(job, SCOPE_FK[scope])
    if scope_id is None:
        raise ValueError(f"report job {job.id} ({scope}) has no target id set")

    data = generate_report_data(
        scope, scope_id,
        progress_cb=lambda current, total: heartbeat(job, current, total),
    )

    report = Report.query.filter_by(
        scope=scope, report_type="v2", **{SCOPE_FK[scope]: scope_id}
    ).first()
    if report is None:
        report = Report(scope=scope, report_type="v2",
                        **{SCOPE_FK[scope]: scope_id})
        db.session.add(report)

    report.report_data = json.dumps(data)
    report.generated_at = data["generated_at"]
    report.analyzer_version = data["analyzer_version"]
    # Ownership denormalized onto the row for listing/access checks; follows
    # current resolution on regenerate (for account/participant scopes these
    # coincide with the scope-target column and are identical values).
    report.provider_id = data["provider_id"]
    report.patient_id = data["patient_id"]
    db.session.flush()
    job.report_id = report.id
    db.session.commit()


_HANDLERS = {
    "extract": _handle_extract,
    "backfill": _handle_backfill,
    "report": _handle_report,
}


def execute_job(job):
    """Run one claimed job to completion, capturing failure on the row.
    Handlers are idempotent, so a job that failed midway can safely re-run."""
    try:
        handler = _HANDLERS.get(job.kind)
        if handler is None:
            raise ValueError(f"unknown job kind: {job.kind!r}")
        handler(job)
    except Exception:
        db.session.rollback()
        job = db.session.merge(job)
        job.status = "failed"
        job.error = traceback.format_exc()
        job.finished_at = _now()
        db.session.commit()
        return job
    job.status = "done"
    job.error = None
    job.finished_at = _now()
    db.session.commit()
    return job


def run_once():
    """One worker iteration: reclaim expired leases, claim, execute.
    Returns the executed job, or None if the queue was empty."""
    reclaim_stale_jobs()
    job = claim_next_job()
    if job is not None:
        execute_job(job)
    return job
