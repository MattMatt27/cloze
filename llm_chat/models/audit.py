import time
from ..extensions import db


class AuditLog(db.Model):
    """Track admin actions for accountability."""
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer)
    details = db.Column(db.Text)  # JSON
    created_at = db.Column(db.Float, default=lambda: time.time())

    actor = db.relationship('User', foreign_keys=[actor_id])

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'actor_id': self.actor_id,
            'actor_name': self.actor.username if self.actor else 'Unknown',
            'action': self.action,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'details': json.loads(self.details) if self.details else {},
            'created_at': self.created_at,
        }


class EscalationEvent(db.Model):
    """Safety-related escalation events surfaced on the admin dashboard."""
    __tablename__ = 'escalation_events'

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)      # conflict, missing_plan, plan_change, sentiment_alert
    severity = db.Column(db.String(20), nullable=False)         # info, warning, critical
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    safety_plan_id = db.Column(db.Integer, db.ForeignKey('safety_plans.id'), nullable=True)
    description = db.Column(db.Text, nullable=False)
    context = db.Column(db.Text)  # JSON
    status = db.Column(db.String(20), default='new', nullable=False)  # new, acknowledged, resolved
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    acknowledged_at = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.Float, default=lambda: time.time())

    patient = db.relationship('User', foreign_keys=[patient_id])
    provider = db.relationship('User', foreign_keys=[provider_id])
    acknowledger = db.relationship('User', foreign_keys=[acknowledged_by])

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'event_type': self.event_type,
            'severity': self.severity,
            'patient_id': self.patient_id,
            'patient_name': self.patient.username if self.patient else 'Unknown',
            'provider_id': self.provider_id,
            'provider_name': self.provider.username if self.provider else None,
            'safety_plan_id': self.safety_plan_id,
            'description': self.description,
            'context': json.loads(self.context) if self.context else {},
            'status': self.status,
            'acknowledged_by': self.acknowledger.username if self.acknowledger else None,
            'acknowledged_at': self.acknowledged_at,
            'created_at': self.created_at,
        }
