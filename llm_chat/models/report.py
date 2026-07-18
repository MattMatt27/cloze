import time
import json
from ..extensions import db


class Report(db.Model):
    """Generated reports.

    v1 rows are per-window (scope NULL, treated as 'window'). Report-v2 rows
    carry an explicit scope plus exactly one matching scope FK:
        conversation → conversation_id      window      → window_id
        enrollment   → flow_enrollment_id   participant → patient_id
        flow         → flow_id              account     → provider_id
    window_id / patient_id / provider_id are nullable since v2 — a flow or
    account report has no single patient; a conversation report may predate
    any window. (Prod: migrate_schema.py relaxes the legacy NOT NULLs.)
    """
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    window_id = db.Column(db.Integer, db.ForeignKey('chat_windows.id'), nullable=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    report_type = db.Column(db.String(50), default='default')  # legacy: default/summary/detailed; v2 rows: 'v2'
    report_data = db.Column(db.Text)  # JSON data containing report details
    generated_at = db.Column(db.Float, default=lambda: time.time())
    file_path = db.Column(db.String(255))  # Path to saved report file if applicable

    # Report-v2 scope linkage (NULL on legacy rows → read as scope='window')
    scope = db.Column(db.String(20), nullable=True, index=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=True)
    flow_enrollment_id = db.Column(db.Integer, db.ForeignKey('flow_enrollments.id'), nullable=True)
    flow_id = db.Column(db.Integer, db.ForeignKey('study_flows.id'), nullable=True)
    analyzer_version = db.Column(db.String(20), nullable=True)  # artifacts version folded in
    template_id = db.Column(db.Integer, db.ForeignKey('report_templates.id'), nullable=True)

    # Relationships
    window = db.relationship('ChatWindow', backref='reports')
    patient = db.relationship('User', foreign_keys=[patient_id], backref='patient_reports')
    provider = db.relationship('User', foreign_keys=[provider_id])

    @property
    def effective_scope(self):
        return self.scope or 'window'

    def to_dict(self):
        return {
            'id': self.id,
            'window_id': self.window_id,
            'patient_id': self.patient_id,
            'provider_id': self.provider_id,
            'report_type': self.report_type,
            'report_data': json.loads(self.report_data) if self.report_data else {},
            'generated_at': self.generated_at,
            'file_path': self.file_path,
            'scope': self.effective_scope,
            'conversation_id': self.conversation_id,
            'flow_enrollment_id': self.flow_enrollment_id,
            'flow_id': self.flow_id,
            'analyzer_version': self.analyzer_version,
            'template_id': self.template_id,
        }
