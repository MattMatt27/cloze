import time
from ..extensions import db


class StudyFlow(db.Model):
    """A reusable study structure that generates ChatWindows on enrollment."""
    __tablename__ = 'study_flows'

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    flow_type = db.Column(db.String(20), nullable=False)  # 'always', 'phased', 'recurring'

    # Recurring-specific
    cadence_days = db.Column(db.Integer, nullable=True)
    cycle_count = db.Column(db.Integer, nullable=True)

    # Report settings (inherited by generated windows)
    report_config = db.Column(db.Text, nullable=True)  # JSON

    created_at = db.Column(db.Float, default=lambda: time.time())
    updated_at = db.Column(db.Float, onupdate=lambda: time.time())

    # Relationships
    provider = db.relationship('User', foreign_keys=[provider_id])
    phases = db.relationship('FlowPhase', backref='flow', cascade='all, delete-orphan',
                             order_by='FlowPhase.order_index')
    enrollments = db.relationship('FlowEnrollment', backref='flow', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'provider_id': self.provider_id,
            'name': self.name,
            'flow_type': self.flow_type,
            'cadence_days': self.cadence_days,
            'cycle_count': self.cycle_count,
            'report_config': self.report_config,
            'created_at': self.created_at,
            'phases': [p.to_dict() for p in self.phases],
            'enrollment_count': len(self.enrollments),
        }


class FlowPhase(db.Model):
    """A time-bounded phase within a study flow."""
    __tablename__ = 'flow_phases'

    id = db.Column(db.Integer, primary_key=True)
    flow_id = db.Column(db.Integer, db.ForeignKey('study_flows.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    order_index = db.Column(db.Integer, default=0)

    # Relative timing (days from enrollment)
    start_day = db.Column(db.Integer, default=0)
    end_day = db.Column(db.Integer, nullable=True)  # NULL = no end (always available)

    # Relationships
    chats = db.relationship('FlowChat', backref='phase', cascade='all, delete-orphan',
                            order_by='FlowChat.order_index')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'order_index': self.order_index,
            'start_day': self.start_day,
            'end_day': self.end_day,
            'chats': [c.to_dict() for c in self.chats],
        }


class FlowChat(db.Model):
    """A chat template definition within a flow phase."""
    __tablename__ = 'flow_chats'

    id = db.Column(db.Integer, primary_key=True)
    phase_id = db.Column(db.Integer, db.ForeignKey('flow_phases.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    purpose = db.Column(db.Text, nullable=True)
    model_id = db.Column(db.Integer, db.ForeignKey('models.id'), nullable=False)
    system_prompt_id = db.Column(db.Integer, db.ForeignKey('system_prompts.id'), nullable=True)
    custom_system_prompt = db.Column(db.Text, nullable=True)
    max_messages = db.Column(db.Integer, nullable=True)
    order_index = db.Column(db.Integer, default=0)

    # Relationships
    model = db.relationship('Model')
    system_prompt = db.relationship('SystemPrompt')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'purpose': self.purpose,
            'model_id': self.model_id,
            'model_name': self.model.name if self.model else None,
            'system_prompt_id': self.system_prompt_id,
            'system_prompt_name': self.system_prompt.name if self.system_prompt else None,
            'custom_system_prompt': self.custom_system_prompt,
            'max_messages': self.max_messages,
            'order_index': self.order_index,
        }


class FlowEnrollment(db.Model):
    """Tracks which patients are enrolled in which flows."""
    __tablename__ = 'flow_enrollments'

    id = db.Column(db.Integer, primary_key=True)
    flow_id = db.Column(db.Integer, db.ForeignKey('study_flows.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    enrolled_at = db.Column(db.Float, default=lambda: time.time())

    # Relationships
    patient = db.relationship('User', foreign_keys=[patient_id])

    __table_args__ = (db.UniqueConstraint('flow_id', 'patient_id'),)

    def to_dict(self):
        return {
            'id': self.id,
            'flow_id': self.flow_id,
            'patient_id': self.patient_id,
            'patient_name': self.patient.username if self.patient else None,
            'enrolled_at': self.enrolled_at,
        }
