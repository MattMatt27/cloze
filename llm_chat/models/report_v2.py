"""Report system v2 — analysis artifacts and the background job queue.

Design: .docs/roadmap/report-system-v2.md

- ``AnalysisArtifact`` holds per-conversation *mergeable sufficient statistics*
  (see ``report/merge.py``). All higher report scopes are folds over artifacts;
  the expensive NLP runs once per conversation, at extraction time.
- ``ReportJob`` is a Postgres-backed job queue row consumed by the dedicated
  worker process (``flask reports-worker``). Claims use FOR UPDATE SKIP LOCKED
  on Postgres; liveness is lease-based via ``heartbeat_at``.

Note: ``template_id`` (per the design doc) is deliberately absent until the
ReportTemplate model lands in the templates milestone — a FK to a nonexistent
table would break ``db.create_all()``.
"""

import time

from ..extensions import db


class AnalysisArtifact(db.Model):
    __tablename__ = 'analysis_artifacts'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer, db.ForeignKey('conversations.id'), nullable=False, index=True
    )
    # Bumping report/extraction.py::ANALYZER_VERSION makes existing rows stale;
    # extraction upserts on (conversation_id, analyzer_version).
    analyzer_version = db.Column(db.String(20), nullable=False)
    artifact_data = db.Column(db.Text)  # JSON — mergeable stats (report/merge.py schema)
    ai_summary = db.Column(db.Text, nullable=True)  # short per-conversation summary
    status = db.Column(db.String(20), nullable=False, default='ready')  # ready | failed
    error = db.Column(db.Text, nullable=True)
    computed_at = db.Column(db.Float, default=lambda: time.time())

    __table_args__ = (
        db.UniqueConstraint('conversation_id', 'analyzer_version', name='uq_artifact_conv_version'),
    )

    conversation = db.relationship('Conversation')


class ReportJob(db.Model):
    __tablename__ = 'report_jobs'

    id = db.Column(db.Integer, primary_key=True)
    # What to do: 'extract' (one conversation's artifact), 'backfill' (all
    # conversations missing current-version artifacts), 'report' (scope report
    # generation — lands with the scope engine milestone).
    kind = db.Column(db.String(20), nullable=False, default='report')
    # For kind='report': which scope. One matching FK below should be set.
    scope = db.Column(db.String(20), nullable=True)  # conversation|window|enrollment|participant|flow|account

    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=True)
    window_id = db.Column(db.Integer, db.ForeignKey('chat_windows.id'), nullable=True)
    flow_enrollment_id = db.Column(db.Integer, db.ForeignKey('flow_enrollments.id'), nullable=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    flow_id = db.Column(db.Integer, db.ForeignKey('study_flows.id'), nullable=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    payload = db.Column(db.Text, nullable=True)  # JSON — job parameters (e.g. force, throttle)
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    status = db.Column(db.String(20), nullable=False, default='queued', index=True)
    # queued | running | done | failed | cancelled
    attempts = db.Column(db.Integer, nullable=False, default=0)  # lease reclaims increment; capped
    progress_current = db.Column(db.Integer, nullable=False, default=0)
    progress_total = db.Column(db.Integer, nullable=False, default=0)
    heartbeat_at = db.Column(db.Float, nullable=True)  # lease liveness; stale running jobs reclaimed
    error = db.Column(db.Text, nullable=True)

    report_id = db.Column(db.Integer, db.ForeignKey('reports.id'), nullable=True)  # result

    created_at = db.Column(db.Float, default=lambda: time.time())
    started_at = db.Column(db.Float, nullable=True)
    finished_at = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'kind': self.kind,
            'scope': self.scope,
            'status': self.status,
            'attempts': self.attempts,
            'progress_current': self.progress_current,
            'progress_total': self.progress_total,
            'error': self.error,
            'report_id': self.report_id,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'finished_at': self.finished_at,
        }
