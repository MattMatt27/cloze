import time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from ..extensions import db

class User(UserMixin, db.Model):
    """User model with role-based access control"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'admin', 'provider', 'user'
    visible = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.Float, default=lambda: time.time())

    # Relationships
    conversations = db.relationship('Conversation', backref='user', foreign_keys='Conversation.user_id', lazy='dynamic')
    saved_selections = db.relationship('SavedSelection', backref='user', foreign_keys='SavedSelection.user_id', lazy='dynamic')
    provider_assignments = db.relationship('ProviderPatient', foreign_keys='ProviderPatient.patient_id', backref='patient', lazy='dynamic')
    patients = db.relationship('ProviderPatient', foreign_keys='ProviderPatient.provider_id', backref='provider', lazy='dynamic')
    safety_plans = db.relationship('SafetyPlan', foreign_keys='SafetyPlan.patient_id', backref='patient_user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_provider(self):
        return self.role == 'provider'

    def is_patient(self):
        return self.role == 'user'

    @property
    def is_active(self):
        """Flask-Login compatibility shim; mirrors the `visible` column."""
        return self.visible

    @is_active.setter
    def is_active(self, value):
        self.visible = value

    @property
    def active_safety_plan(self):
        from .safety_plan import SafetyPlan
        return SafetyPlan.query.filter_by(patient_id=self.id, status='active').first()

    @property
    def has_safety_plan(self):
        return self.active_safety_plan is not None

    def can_access_patient(self, patient_id):
        """Check if user can access a specific patient's data"""
        if self.is_admin():
            return True
        if self.is_provider():
            return ProviderPatient.query.filter_by(
                provider_id=self.id,
                patient_id=patient_id
            ).first() is not None
        return self.id == patient_id

class ProviderPatient(db.Model):
    """Association table for provider-patient relationships"""
    __tablename__ = 'provider_patients'

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_at = db.Column(db.Float, default=lambda: time.time())
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    __table_args__ = (db.UniqueConstraint('provider_id', 'patient_id'),)
