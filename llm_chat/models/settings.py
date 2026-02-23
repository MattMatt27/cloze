import time
from ..extensions import db

class SystemPrompt(db.Model):
    """System prompts for conversations"""
    __tablename__ = 'system_prompts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    domain_prompt_id = db.Column(db.String(50), nullable=True)  # maps to prompts/domains/<id>.md
    visible = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.Float, default=lambda: time.time())
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

class ProviderSettings(db.Model):
    """Settings that providers can configure for their patients"""
    __tablename__ = 'provider_settings'
    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # NULL means applies to all patients
    allowed_models = db.Column(db.Text)  # JSON array of model IDs
    system_prompt_id = db.Column(db.Integer, db.ForeignKey('system_prompts.id'), nullable=True)
    time_window_start = db.Column(db.String(10))  # HH:MM format
    time_window_end = db.Column(db.String(10))    # HH:MM format
    max_messages_per_day = db.Column(db.Integer)
    custom_instructions = db.Column(db.Text)
    created_at = db.Column(db.Float, default=lambda: time.time())
    updated_at = db.Column(db.Float, onupdate=lambda: time.time())

    # Relationships
    provider = db.relationship('User', foreign_keys=[provider_id])
    patient = db.relationship('User', foreign_keys=[patient_id])
    system_prompt = db.relationship('SystemPrompt')

class AdminSettings(db.Model):
    """Global admin settings for system control"""
    __tablename__ = 'admin_settings'
    id = db.Column(db.Integer, primary_key=True)
    setting_name = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.Text)  # JSON value
    description = db.Column(db.Text)
    created_at = db.Column(db.Float, default=lambda: time.time())
    updated_at = db.Column(db.Float, onupdate=lambda: time.time())

class UserSettings(db.Model):
    """Admin-controlled settings for individual users"""
    __tablename__ = 'user_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    allowed_models = db.Column(db.Text)   # JSON array
    blocked_models = db.Column(db.Text)   # JSON array
    can_use_custom_prompts = db.Column(db.Boolean, default=True)
    can_save_selections = db.Column(db.Boolean, default=True)
    max_conversations_per_day = db.Column(db.Integer)
    max_messages_per_conversation = db.Column(db.Integer)
    visible = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.Float, default=lambda: time.time())
    updated_at = db.Column(db.Float, onupdate=lambda: time.time())

    # Relationship
    user = db.relationship('User', backref='settings')
