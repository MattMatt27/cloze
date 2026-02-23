import time
import json
from ..extensions import db

class ChatWindow(db.Model):
    """Represents a time-bounded chat window created by a clinician for a patient"""
    __tablename__ = 'chat_windows'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Float, nullable=False)  # Unix timestamp
    end_date = db.Column(db.Float, nullable=False)    # Unix timestamp
    visible = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='scheduled', nullable=False)
    created_at = db.Column(db.Float, default=lambda: time.time())
    updated_at = db.Column(db.Float, onupdate=lambda: time.time())

    # Report configuration (JSON string storing enabled components)
    report_config = db.Column(db.Text, default='{"ai_summary": true, "saved_messages": true, "descriptive_stats": true, "nlp_analysis": true, "cooccurrence_analysis": true}')

    # Relationships
    patient = db.relationship('User', foreign_keys=[patient_id], backref='chat_windows')
    provider = db.relationship('User', foreign_keys=[provider_id])
    templates = db.relationship('ChatTemplate', backref='window', lazy='dynamic', cascade='all, delete-orphan')
    conversations = db.relationship('Conversation', backref='chat_window', lazy='dynamic')

    def is_current(self):
        """Check if this window is currently active based on date"""
        return self.compute_status() == 'active'

    @property
    def is_active(self):
        """Compatibility shim for legacy code paths."""
        return self.visible and self.compute_status() == 'active'

    def compute_status(self, now=None):
        """Return the status string based on timing and current state."""
        now = now or time.time()

        # Terminal states: these persist regardless of time
        if self.status in ('generating_report', 'report_ready'):
            return self.status

        if now < self.start_date:
            return 'scheduled'
        if self.start_date <= now <= self.end_date:
            return 'active'

        return 'generating_report'

    def sync_status(self, now=None):
        """Update persisted status to match the computed status."""
        new_status = self.compute_status(now)
        if self.status != new_status:
            self.status = new_status
        return self.status

    def is_upcoming(self, now=None):
        """Check if this window is scheduled for the future"""
        return self.compute_status(now) == 'scheduled'

    def get_report_config(self):
        """Get report configuration as normalized v2 dict."""
        from report.config import normalize_config, get_default_config
        try:
            raw = json.loads(self.report_config or '{}')
            return normalize_config(raw)
        except Exception:
            return get_default_config()

    def set_report_config(self, config):
        """Set report configuration from dict"""
        self.report_config = json.dumps(config)

    def get_report_type(self):
        """Get the report type from config."""
        config = self.get_report_config()
        return config.get('report_type', 'summary')

    def to_dict(self):
        status_value = self.compute_status()
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'provider_id': self.provider_id,
            'title': self.title,
            'description': self.description,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'visible': self.visible,
            'status': status_value,
            'is_current': self.is_current(),
            'is_upcoming': self.is_upcoming(),
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'report_config': self.get_report_config(),
        }


class ChatTemplate(db.Model):
    """Predefined chat configuration within a window"""
    __tablename__ = 'chat_templates'

    id = db.Column(db.Integer, primary_key=True)
    window_id = db.Column(db.Integer, db.ForeignKey('chat_windows.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    purpose = db.Column(db.Text)  # Description of what this chat is for
    model_id = db.Column(db.Integer, db.ForeignKey('models.id'), nullable=False)
    system_prompt_id = db.Column(db.Integer, db.ForeignKey('system_prompts.id'), nullable=True)
    custom_system_prompt = db.Column(db.Text)  # If not using a predefined prompt
    max_messages = db.Column(db.Integer)  # Optional limit on messages in this chat
    order_index = db.Column(db.Integer, default=0)  # Display order
    visible = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.Float, default=lambda: time.time())

    # Relationships
    model = db.relationship('Model')
    system_prompt = db.relationship('SystemPrompt')

    def get_system_prompt_content(self):
        """Get the actual system prompt content to use"""
        base_content = ""

        # Start with the selected system prompt
        if self.system_prompt:
            base_content = self.system_prompt.content

        # Add custom instructions if provided
        if self.custom_system_prompt and self.custom_system_prompt.strip():
            if base_content:
                # Combine base prompt with custom instructions
                base_content = f"{base_content}\n\nAdditional Instructions: {self.custom_system_prompt.strip()}"
            else:
                # Use only custom instructions if no base prompt selected
                base_content = self.custom_system_prompt.strip()

        return base_content if base_content else None

    def to_dict(self):
        return {
            'id': self.id,
            'window_id': self.window_id,
            'title': self.title,
            'purpose': self.purpose,
            'model': self.model.name if self.model else None,
            'model_id': self.model_id,
            'system_prompt_id': self.system_prompt_id,
            'custom_system_prompt': self.custom_system_prompt,
            'max_messages': self.max_messages,
            'order_index': self.order_index,
            'visible': self.visible,
            'created_at': self.created_at
        }
