import json
import time
from ..extensions import db


# Severity/effectiveness labels for display
SEVERITY_LABELS = {1: 'mild', 2: 'mild-moderate', 3: 'moderate', 4: 'moderate-severe', 5: 'severe'}
EFFECTIVENESS_LABELS = {1: 'minimal', 2: 'low', 3: 'moderate', 4: 'high', 5: 'very high'}
COMFORT_LABELS = {1: 'very low', 2: 'low', 3: 'moderate', 4: 'high', 5: 'very high'}
ANTI_PATTERN_SEVERITY_LABELS = {1: 'minor', 2: 'moderate', 3: 'critical'}


class SafetyPlan(db.Model):
    """Personalized safety plan based on the Stanley-Brown Safety Planning Intervention.

    Each row is a versioned snapshot. Status lifecycle:
        draft -> pending_review -> active -> superseded
    """
    __tablename__ = 'safety_plans'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='draft')
    version = db.Column(db.Integer, default=1)

    # Patient-authored sections (JSON)
    warning_signs = db.Column(db.Text)        # [{sign, severity, context}]
    coping_strategies = db.Column(db.Text)    # [{strategy, effectiveness, context, patient_language}]
    support_network = db.Column(db.Text)      # [{person, relationship, contact_preference, comfort_level}]
    reasons_for_living = db.Column(db.Text)   # [{reason, context}]

    # Provider-authored sections (JSON)
    anti_patterns = db.Column(db.Text)        # [{pattern, reason, severity, source, visible_to_patient, conflicts_with, conflict_rationale}]
    care_team = db.Column(db.Text)            # [{name, role, contact_protocol, after_hours}]
    emergency_plan = db.Column(db.Text)       # {activation_conditions, preferred_facility, contraindications}
    provider_notes = db.Column(db.Text)       # Free-text clinical notes (never shown to patient)

    # Metadata
    created_at = db.Column(db.Float, default=lambda: time.time())
    updated_at = db.Column(db.Float, onupdate=lambda: time.time())
    approved_at = db.Column(db.Float, nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationships
    patient = db.relationship('User', foreign_keys=[patient_id], overlaps='patient_user,safety_plans')
    approver = db.relationship('User', foreign_keys=[approved_by])

    # --- JSON accessors ---

    def _get_json(self, column_value):
        if not column_value:
            return []
        try:
            return json.loads(column_value)
        except (json.JSONDecodeError, TypeError):
            return []

    def _get_json_dict(self, column_value):
        if not column_value:
            return {}
        try:
            return json.loads(column_value)
        except (json.JSONDecodeError, TypeError):
            return {}

    def _set_json(self, value):
        return json.dumps(value) if value is not None else None

    def get_warning_signs(self):
        return self._get_json(self.warning_signs)

    def set_warning_signs(self, data):
        self.warning_signs = self._set_json(data)

    def get_coping_strategies(self):
        return self._get_json(self.coping_strategies)

    def set_coping_strategies(self, data):
        self.coping_strategies = self._set_json(data)

    def get_support_network(self):
        return self._get_json(self.support_network)

    def set_support_network(self, data):
        self.support_network = self._set_json(data)

    def get_reasons_for_living(self):
        return self._get_json(self.reasons_for_living)

    def set_reasons_for_living(self, data):
        self.reasons_for_living = self._set_json(data)

    def get_anti_patterns(self, include_hidden=True):
        items = self._get_json(self.anti_patterns)
        if not include_hidden:
            items = [ap for ap in items if ap.get('visible_to_patient', True)]
        return items

    def set_anti_patterns(self, data):
        self.anti_patterns = self._set_json(data)

    def get_care_team(self):
        return self._get_json(self.care_team)

    def set_care_team(self, data):
        self.care_team = self._set_json(data)

    def get_emergency_plan(self):
        return self._get_json_dict(self.emergency_plan)

    def set_emergency_plan(self, data):
        self.emergency_plan = self._set_json(data)

    # --- Status helpers ---

    @classmethod
    def get_active_plan(cls, patient_id):
        return cls.query.filter_by(patient_id=patient_id, status='active').first()

    @classmethod
    def get_pending_plan(cls, patient_id):
        return cls.query.filter_by(patient_id=patient_id, status='pending_review').first()

    def is_complete(self):
        """True if patient sections are filled in."""
        return bool(
            self.get_warning_signs()
            and self.get_coping_strategies()
            and self.get_support_network()
            and self.get_reasons_for_living()
        )

    def is_provider_complete(self):
        """True if provider sections are filled in."""
        return bool(
            self.get_anti_patterns()
            and self.get_care_team()
            and self.get_emergency_plan()
        )

    # --- Prompt integration ---

    def to_prompt_dict(self):
        """Structured dict for the prompt composer."""
        anti_patterns = self.get_anti_patterns(include_hidden=True)
        # Identify conflicts
        conflicts = []
        for ap in anti_patterns:
            if ap.get('conflicts_with') is not None:
                conflicts.append(ap)

        return {
            'warning_signs': self.get_warning_signs(),
            'coping_strategies': self.get_coping_strategies(),
            'support_network': self.get_support_network(),
            'care_team': self.get_care_team(),
            'emergency_plan': self.get_emergency_plan(),
            'reasons_for_living': self.get_reasons_for_living(),
            'anti_patterns': anti_patterns,
            'conflicts': conflicts,
        }

    # --- Serialization ---

    def to_dict(self, for_patient=False):
        """Serialize for API responses.

        Args:
            for_patient: If True, hide provider_notes and hidden anti-patterns.
        """
        result = {
            'id': self.id,
            'patient_id': self.patient_id,
            'status': self.status,
            'version': self.version,
            'warning_signs': self.get_warning_signs(),
            'coping_strategies': self.get_coping_strategies(),
            'support_network': self.get_support_network(),
            'reasons_for_living': self.get_reasons_for_living(),
            'anti_patterns': self.get_anti_patterns(include_hidden=not for_patient),
            'care_team': self.get_care_team(),
            'emergency_plan': self.get_emergency_plan(),
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'approved_at': self.approved_at,
            'approved_by': self.approved_by,
        }
        if not for_patient:
            result['provider_notes'] = self.provider_notes
        return result
