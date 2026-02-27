import json
import time
from flask import Blueprint, render_template, jsonify, request
from flask_login import current_user
from ..utils.decorators import role_required
from ..extensions import db
from ..models import (
    User, ProviderPatient, Conversation, Message,
    AdminSettings, UserSettings, ChatWindow, ChatTemplate,
    Report, SafetyPlan, Model, SystemPrompt,
    AuditLog, EscalationEvent,
)

admin_bp = Blueprint("admin", __name__, url_prefix="")


# ── Helpers ────────────────────────────────────────────────────

def _get_admin_setting(name, default=None):
    """Read a single admin setting value."""
    row = AdminSettings.query.filter_by(setting_name=name).first()
    if not row or not row.setting_value:
        return default
    try:
        return json.loads(row.setting_value)
    except Exception:
        return row.setting_value


def _log_action(action, target_type, target_id=None, details=None):
    """Write an audit-log entry for the current admin."""
    entry = AuditLog(
        actor_id=current_user.id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=json.dumps(details) if details else None,
    )
    db.session.add(entry)


# ── Pages ──────────────────────────────────────────────────────

@admin_bp.route("/admin/dashboard")
@role_required('admin')
def admin_dashboard():
    return render_template("admin_dashboard.html")


@admin_bp.route("/admin/transcript/<int:conversation_id>")
@role_required('admin')
def admin_transcript(conversation_id):
    """Read-only transcript view for admin."""
    conversation = Conversation.query.get_or_404(conversation_id)
    return render_template(
        "conversation.html",
        conversation_id=conversation_id,
        readonly=True,
    )


# ── Stats ──────────────────────────────────────────────────────

@admin_bp.route("/api/admin/stats")
@role_required('admin')
def get_admin_stats():
    total_users = User.query.count()
    total_providers = User.query.filter_by(role='provider').count()
    total_patients = User.query.filter_by(role='user').count()
    total_conversations = Conversation.query.count()
    total_reports = Report.query.count()
    active_windows = ChatWindow.query.filter_by(status='active').count()
    pending_plans = SafetyPlan.query.filter_by(status='pending_review').count()

    # Patients with windows but no active safety plan
    patients_with_windows = db.session.query(ChatWindow.patient_id).distinct().subquery()
    patients_with_active_plan = db.session.query(SafetyPlan.patient_id).filter_by(status='active').subquery()
    missing_plan_count = db.session.query(User.id).filter(
        User.id.in_(db.session.query(patients_with_windows)),
        ~User.id.in_(db.session.query(patients_with_active_plan)),
    ).count()

    return jsonify({
        'total_users': total_users,
        'total_providers': total_providers,
        'total_patients': total_patients,
        'total_conversations': total_conversations,
        'total_reports': total_reports,
        'active_windows': active_windows,
        'pending_plans': pending_plans,
        'missing_plan_count': missing_plan_count,
    })


# ── Users ──────────────────────────────────────────────────────

@admin_bp.route("/api/admin/users")
@role_required('admin')
def get_all_users():
    users = User.query.all()
    user_data = []
    for u in users:
        if u.role == 'user':
            conversation_count = Conversation.query.filter_by(user_id=u.id).count()
        elif u.role == 'provider':
            assigned_patients = ProviderPatient.query.filter_by(provider_id=u.id).all()
            patient_ids = [pp.patient_id for pp in assigned_patients]
            conversation_count = Conversation.query.filter(Conversation.user_id.in_(patient_ids)).count() if patient_ids else 0
        else:
            conversation_count = 0
        user_data.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'role': u.role,
            'visible': u.visible,
            'created_at': u.created_at,
            'conversation_count': conversation_count
        })
    return jsonify(user_data)


@admin_bp.route("/api/admin/user", methods=['POST'])
@role_required('admin')
def create_user():
    data = request.json or {}
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    user = User(username=data['username'], email=data['email'], role=data['role'])
    user.set_password(data['password'])
    db.session.add(user)
    _log_action('user_created', 'user', details={
        'username': data['username'], 'role': data['role'],
    })
    db.session.commit()
    return jsonify({'id': user.id})


@admin_bp.route("/api/admin/user/<int:user_id>/toggle-visibility", methods=['POST'])
@role_required('admin')
def toggle_user_visibility(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json or {}
    new_visible = data.get('visible', not user.visible)
    old_visible = user.visible
    user.visible = new_visible
    _log_action('user_disabled' if not new_visible else 'user_enabled', 'user', user_id, {
        'before': old_visible, 'after': new_visible,
    })
    db.session.commit()
    return jsonify({'status': 'success', 'visible': user.visible})


@admin_bp.route("/api/admin/user/<int:user_id>/reset-password", methods=['POST'])
@role_required('admin')
def reset_user_password(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json or {}
    new_password = data.get('password')
    if not new_password or len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    user.set_password(new_password)
    _log_action('password_reset', 'user', user_id)
    db.session.commit()
    return jsonify({'status': 'success'})


# ── Patient management ─────────────────────────────────────────

@admin_bp.route("/api/admin/patients")
@role_required('admin')
def get_all_patients():
    """All patients with extended info for the patient management tab."""
    patients = User.query.filter_by(role='user').all()
    result = []
    for p in patients:
        # Provider assignment
        assignment = ProviderPatient.query.filter_by(patient_id=p.id).first()
        provider = User.query.get(assignment.provider_id) if assignment else None

        # Safety plan
        active_plan = SafetyPlan.get_active_plan(p.id)
        pending_plan = SafetyPlan.get_pending_plan(p.id)
        draft_plan = SafetyPlan.query.filter_by(patient_id=p.id, status='draft').first()
        plan_status = 'active' if active_plan else 'pending' if pending_plan else 'draft' if draft_plan else 'none'

        # Windows
        window_count = ChatWindow.query.filter_by(patient_id=p.id, visible=True).count()
        active_windows = ChatWindow.query.filter_by(patient_id=p.id, status='active', visible=True).count()

        # Last activity
        last_conv = Conversation.query.filter_by(user_id=p.id).order_by(Conversation.updated_at.desc()).first()
        last_activity = (last_conv.updated_at or last_conv.created_at) if last_conv else None

        result.append({
            'id': p.id,
            'username': p.username,
            'email': p.email,
            'visible': p.visible,
            'created_at': p.created_at,
            'provider_id': provider.id if provider else None,
            'provider_name': provider.username if provider else None,
            'plan_status': plan_status,
            'window_count': window_count,
            'active_windows': active_windows,
            'last_activity': last_activity,
        })
    return jsonify(result)


@admin_bp.route("/api/admin/patient/<int:patient_id>/details")
@role_required('admin')
def get_patient_details(patient_id):
    """Drill-down data for a single patient."""
    patient = User.query.get_or_404(patient_id)

    # Assignment
    assignment = ProviderPatient.query.filter_by(patient_id=patient_id).first()
    provider = User.query.get(assignment.provider_id) if assignment else None

    # Safety plans
    active_plan = SafetyPlan.get_active_plan(patient_id)
    pending_plan = SafetyPlan.get_pending_plan(patient_id)
    draft_plan = SafetyPlan.query.filter_by(patient_id=patient_id, status='draft').first()

    # All safety plan versions
    all_plans = SafetyPlan.query.filter_by(patient_id=patient_id).order_by(SafetyPlan.version.desc()).all()

    # Chat windows
    windows = ChatWindow.query.filter_by(patient_id=patient_id).order_by(ChatWindow.created_at.desc()).all()
    window_data = []
    for w in windows:
        convs = Conversation.query.filter_by(user_id=patient_id, window_id=w.id).all()
        reports = Report.query.filter_by(window_id=w.id, patient_id=patient_id).all()
        window_data.append({
            'id': w.id,
            'title': w.title,
            'status': w.compute_status(),
            'start_date': w.start_date,
            'end_date': w.end_date,
            'conversations': [{
                'id': c.id,
                'title': c.title,
                'model': c.model.name if c.model else None,
                'message_count': c.messages.count(),
                'created_at': c.created_at,
                'updated_at': c.updated_at,
            } for c in convs],
            'reports': [{
                'id': r.id,
                'report_type': r.report_type,
                'generated_at': r.generated_at,
            } for r in reports],
        })

    # All providers for reassignment dropdown
    all_providers = User.query.filter_by(role='provider').all()

    return jsonify({
        'id': patient.id,
        'username': patient.username,
        'email': patient.email,
        'visible': patient.visible,
        'created_at': patient.created_at,
        'provider_id': provider.id if provider else None,
        'provider_name': provider.username if provider else None,
        'assignment_id': assignment.id if assignment else None,
        'safety_plan': {
            'active': active_plan.to_dict() if active_plan else None,
            'pending': pending_plan.to_dict() if pending_plan else None,
            'draft': draft_plan.to_dict() if draft_plan else None,
            'history': [{'id': p.id, 'version': p.version, 'status': p.status,
                         'created_at': p.created_at, 'approved_at': p.approved_at}
                        for p in all_plans],
        },
        'windows': window_data,
        'all_providers': [{'id': pv.id, 'username': pv.username} for pv in all_providers],
    })


@admin_bp.route("/api/admin/patient/<int:patient_id>/reassign", methods=['POST'])
@role_required('admin')
def reassign_patient(patient_id):
    """Reassign a patient to a different provider."""
    data = request.json or {}
    new_provider_id = data.get('provider_id')
    if not new_provider_id:
        return jsonify({'error': 'provider_id is required'}), 400

    new_provider = User.query.get(new_provider_id)
    if not new_provider or new_provider.role != 'provider':
        return jsonify({'error': 'Invalid provider'}), 400

    # Remove existing assignment
    old_assignment = ProviderPatient.query.filter_by(patient_id=patient_id).first()
    old_provider_id = old_assignment.provider_id if old_assignment else None
    if old_assignment:
        db.session.delete(old_assignment)

    # Create new assignment
    assignment = ProviderPatient(
        provider_id=new_provider_id,
        patient_id=patient_id,
        assigned_by=current_user.id,
    )
    db.session.add(assignment)
    _log_action('assignment_changed', 'assignment', patient_id, {
        'old_provider_id': old_provider_id, 'new_provider_id': new_provider_id,
    })
    db.session.commit()
    return jsonify({'status': 'success'})


# ── Provider management ────────────────────────────────────────

@admin_bp.route("/api/admin/providers")
@role_required('admin')
def get_all_providers():
    """All providers with extended info for the provider management tab."""
    providers = User.query.filter_by(role='provider').all()
    result = []
    for pv in providers:
        assignments = ProviderPatient.query.filter_by(provider_id=pv.id).all()
        patient_ids = [a.patient_id for a in assignments]
        patient_count = len(patient_ids)

        active_windows = ChatWindow.query.filter_by(
            provider_id=pv.id, status='active', visible=True
        ).count()

        # Last activity across all patients
        last_conv = None
        if patient_ids:
            last_conv = Conversation.query.filter(
                Conversation.user_id.in_(patient_ids)
            ).order_by(Conversation.updated_at.desc()).first()
        last_activity = (last_conv.updated_at or last_conv.created_at) if last_conv else None

        result.append({
            'id': pv.id,
            'username': pv.username,
            'email': pv.email,
            'visible': pv.visible,
            'created_at': pv.created_at,
            'patient_count': patient_count,
            'active_windows': active_windows,
            'last_activity': last_activity,
        })
    return jsonify(result)


@admin_bp.route("/api/admin/provider/<int:provider_id>/details")
@role_required('admin')
def get_provider_details(provider_id):
    """Drill-down data for a single provider."""
    provider = User.query.get_or_404(provider_id)

    assignments = ProviderPatient.query.filter_by(provider_id=provider_id).all()
    patients = []
    for a in assignments:
        patient = User.query.get(a.patient_id)
        if patient:
            last_conv = Conversation.query.filter_by(user_id=patient.id).order_by(Conversation.updated_at.desc()).first()
            plan = SafetyPlan.get_active_plan(patient.id)
            patients.append({
                'id': patient.id,
                'username': patient.username,
                'email': patient.email,
                'plan_status': 'active' if plan else 'none',
                'last_activity': (last_conv.updated_at or last_conv.created_at) if last_conv else None,
            })

    windows = ChatWindow.query.filter_by(provider_id=provider_id).order_by(ChatWindow.created_at.desc()).all()
    window_data = []
    for w in windows:
        patient = User.query.get(w.patient_id)
        reports = Report.query.filter_by(window_id=w.id).all()
        window_data.append({
            'id': w.id,
            'title': w.title,
            'status': w.compute_status(),
            'patient_name': patient.username if patient else 'Unknown',
            'patient_id': w.patient_id,
            'start_date': w.start_date,
            'end_date': w.end_date,
            'report_count': len(reports),
        })

    # Unassigned patients for assignment dropdown
    assigned_ids = {a.patient_id for a in assignments}
    unassigned = User.query.filter(
        User.role == 'user',
        ~User.id.in_(assigned_ids) if assigned_ids else True,
    ).all()

    return jsonify({
        'id': provider.id,
        'username': provider.username,
        'email': provider.email,
        'visible': provider.visible,
        'patients': patients,
        'windows': window_data,
        'unassigned_patients': [{'id': u.id, 'username': u.username} for u in unassigned],
    })


@admin_bp.route("/api/admin/provider/<int:provider_id>/patients")
@role_required('admin')
def admin_get_provider_patients(provider_id):
    assignments = ProviderPatient.query.filter_by(provider_id=provider_id).all()
    patient_ids = [a.patient_id for a in assignments]
    patients = User.query.filter(User.id.in_(patient_ids)).all() if patient_ids else []

    def last_active_for(u):
        conv = Conversation.query.filter_by(user_id=u.id).order_by(Conversation.updated_at.desc()).first()
        return conv.updated_at if conv else None

    data = []
    for patient in patients:
        conversation_count = Conversation.query.filter_by(user_id=patient.id).count()
        data.append({
            'id': patient.id,
            'username': patient.username,
            'email': patient.email,
            'conversation_count': conversation_count,
            'last_active': last_active_for(patient),
        })
    return jsonify(data)


# ── Assignments ────────────────────────────────────────────────

@admin_bp.route("/api/admin/assignments")
@role_required('admin')
def get_provider_assignments():
    assignment_data = []
    for assignment in ProviderPatient.query.all():
        provider = User.query.get(assignment.provider_id)
        patient = User.query.get(assignment.patient_id)
        assigned_by = User.query.get(assignment.assigned_by)
        assignment_data.append({
            'id': assignment.id,
            'provider_id': assignment.provider_id,
            'provider_name': provider.username if provider else 'Unknown',
            'patient_id': assignment.patient_id,
            'patient_name': patient.username if patient else 'Unknown',
            'assigned_by': assigned_by.username if assigned_by else 'Unknown',
            'created_at': assignment.assigned_at,
        })
    return jsonify(assignment_data)


@admin_bp.route("/api/admin/assign_provider", methods=['POST'])
@role_required('admin')
def assign_provider():
    data = request.json or {}
    existing = ProviderPatient.query.filter_by(
        provider_id=data['provider_id'], patient_id=data['patient_id']
    ).first()
    if existing:
        return jsonify({'error': 'Assignment already exists'}), 400
    assignment = ProviderPatient(
        provider_id=data['provider_id'],
        patient_id=data['patient_id'],
        assigned_by=current_user.id,
    )
    db.session.add(assignment)
    _log_action('assignment_created', 'assignment', details={
        'provider_id': data['provider_id'], 'patient_id': data['patient_id'],
    })
    db.session.commit()
    return jsonify({'status': 'success'})


@admin_bp.route("/api/admin/assignment/<int:assignment_id>", methods=['DELETE'])
@role_required('admin')
def remove_assignment(assignment_id):
    assignment = ProviderPatient.query.get_or_404(assignment_id)
    _log_action('assignment_removed', 'assignment', assignment_id, {
        'provider_id': assignment.provider_id, 'patient_id': assignment.patient_id,
    })
    db.session.delete(assignment)
    db.session.commit()
    return jsonify({'status': 'success'})


# ── Conversations (admin view) ─────────────────────────────────

@admin_bp.route("/api/admin/user/<int:user_id>/conversations")
@role_required('admin')
def get_user_conversations(user_id):
    conversations = Conversation.query.filter_by(user_id=user_id).order_by(Conversation.created_at.desc()).all()
    payload = []
    for conv in conversations:
        message_count = Message.query.filter_by(conversation_id=conv.id).count()
        payload.append({
            'id': conv.id,
            'title': conv.title,
            'model': conv.model.name if conv.model else None,
            'created_at': conv.created_at,
            'updated_at': conv.updated_at,
            'message_count': message_count
        })
    return jsonify(payload)


@admin_bp.route("/api/admin/conversation/<int:conversation_id>/messages")
@role_required('admin')
def get_conversation_messages(conversation_id):
    """Get all messages for a conversation (admin transcript viewer API)."""
    conversation = Conversation.query.get_or_404(conversation_id)
    messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.timestamp).all()
    return jsonify({
        'conversation': {
            'id': conversation.id,
            'title': conversation.title,
            'model': conversation.model.name if conversation.model else None,
            'created_at': conversation.created_at,
            'user_id': conversation.user_id,
        },
        'messages': [m.to_dict() for m in messages],
    })


# ── Settings ───────────────────────────────────────────────────

@admin_bp.route("/api/admin/settings")
@role_required('admin')
def get_admin_settings():
    settings = AdminSettings.query.all()
    settings_dict = {}
    for setting in settings:
        try:
            settings_dict[setting.setting_name] = json.loads(setting.setting_value) if setting.setting_value else None
        except Exception:
            settings_dict[setting.setting_name] = setting.setting_value
    return jsonify(settings_dict)


@admin_bp.route("/api/admin/settings", methods=['POST'])
@role_required('admin')
def update_admin_settings():
    data = request.json or {}
    for setting_name, setting_value in data.items():
        existing = AdminSettings.query.filter_by(setting_name=setting_name).first()
        value = json.dumps(setting_value) if isinstance(setting_value, (dict, list)) else str(setting_value)
        if existing:
            old_value = existing.setting_value
            existing.setting_value = value
            existing.updated_at = time.time()
        else:
            old_value = None
            db.session.add(AdminSettings(setting_name=setting_name, setting_value=value))
        _log_action('setting_changed', 'setting', details={
            'setting': setting_name, 'old': old_value, 'new': value,
        })
    db.session.commit()
    return jsonify({'status': 'success'})


@admin_bp.route("/api/admin/user/<int:user_id>/settings")
@role_required('admin')
def get_user_settings(user_id):
    user_settings = UserSettings.query.filter_by(user_id=user_id).first()
    if not user_settings:
        return jsonify({
            'user_id': user_id,
            'allowed_models': [],
            'blocked_models': [],
            'can_use_custom_prompts': True,
            'can_save_selections': True,
            'max_conversations_per_day': None,
            'max_messages_per_conversation': None,
            'visible': True
        })
    return jsonify({
        'user_id': user_settings.user_id,
        'allowed_models': json.loads(user_settings.allowed_models) if user_settings.allowed_models else [],
        'blocked_models': json.loads(user_settings.blocked_models) if user_settings.blocked_models else [],
        'can_use_custom_prompts': user_settings.can_use_custom_prompts,
        'can_save_selections': user_settings.can_save_selections,
        'max_conversations_per_day': user_settings.max_conversations_per_day,
        'max_messages_per_conversation': user_settings.max_messages_per_conversation,
        'visible': user_settings.visible
    })


@admin_bp.route("/api/admin/user/<int:user_id>/settings", methods=['POST'])
@role_required('admin')
def update_user_settings(user_id):
    data = request.json or {}
    user_settings = UserSettings.query.filter_by(user_id=user_id).first()
    if not user_settings:
        user_settings = UserSettings(user_id=user_id)
        db.session.add(user_settings)

    if 'allowed_models' in data:
        user_settings.allowed_models = json.dumps(data['allowed_models'])
    if 'blocked_models' in data:
        user_settings.blocked_models = json.dumps(data['blocked_models'])
    if 'can_use_custom_prompts' in data:
        user_settings.can_use_custom_prompts = data['can_use_custom_prompts']
    if 'can_save_selections' in data:
        user_settings.can_save_selections = data['can_save_selections']
    if 'max_conversations_per_day' in data:
        user_settings.max_conversations_per_day = data['max_conversations_per_day']
    if 'max_messages_per_conversation' in data:
        user_settings.max_messages_per_conversation = data['max_messages_per_conversation']
    if 'visible' in data:
        user_settings.visible = data['visible']
    elif 'is_active' in data:
        user_settings.visible = data['is_active']

    user_settings.updated_at = time.time()
    db.session.commit()
    return jsonify({'status': 'success'})


# ── Model management ───────────────────────────────────────────

@admin_bp.route("/api/admin/models")
@role_required('admin')
def get_all_models():
    models = Model.query.all()
    return jsonify([{
        'id': m.id,
        'name': m.name,
        'provider': m.provider,
        'model_identifier': m.model_identifier,
        'api_endpoint': m.api_endpoint,
        'config': json.loads(m.config) if m.config else {},
        'visible': m.visible,
        'is_available': m.is_available,
        'created_at': m.created_at,
    } for m in models])


@admin_bp.route("/api/admin/models", methods=['POST'])
@role_required('admin')
def create_model():
    data = request.json or {}
    model = Model(
        name=data['name'],
        provider=data.get('provider', ''),
        model_identifier=data.get('model_identifier', ''),
        api_endpoint=data.get('api_endpoint'),
        config=json.dumps(data.get('config', {})),
        visible=data.get('visible', True),
    )
    db.session.add(model)
    _log_action('model_created', 'model', details={'name': data['name']})
    db.session.commit()
    return jsonify({'id': model.id})


@admin_bp.route("/api/admin/models/<int:model_id>", methods=['PUT'])
@role_required('admin')
def update_model(model_id):
    model = Model.query.get_or_404(model_id)
    data = request.json or {}

    if 'name' in data:
        model.name = data['name']
    if 'provider' in data:
        model.provider = data['provider']
    if 'model_identifier' in data:
        model.model_identifier = data['model_identifier']
    if 'api_endpoint' in data:
        model.api_endpoint = data['api_endpoint']
    if 'config' in data:
        model.config = json.dumps(data['config'])
    if 'visible' in data:
        model.visible = data['visible']

    _log_action('model_updated', 'model', model_id, {'name': model.name})
    db.session.commit()
    return jsonify({'status': 'success'})


@admin_bp.route("/api/admin/models/<int:model_id>/toggle", methods=['POST'])
@role_required('admin')
def toggle_model(model_id):
    model = Model.query.get_or_404(model_id)
    model.visible = not model.visible
    _log_action('model_toggled', 'model', model_id, {
        'name': model.name, 'visible': model.visible,
    })
    db.session.commit()
    return jsonify({'status': 'success', 'visible': model.visible})


# ── Safety plan queries ────────────────────────────────────────

@admin_bp.route("/api/admin/safety-plans/pending")
@role_required('admin')
def get_pending_plans():
    """Safety plans awaiting provider review."""
    pending = SafetyPlan.query.filter_by(status='pending_review').all()
    result = []
    for plan in pending:
        patient = User.query.get(plan.patient_id)
        # Find assigned provider
        assignment = ProviderPatient.query.filter_by(patient_id=plan.patient_id).first()
        provider = User.query.get(assignment.provider_id) if assignment else None
        result.append({
            'plan_id': plan.id,
            'patient_id': plan.patient_id,
            'patient_name': patient.username if patient else 'Unknown',
            'provider_name': provider.username if provider else 'Unassigned',
            'version': plan.version,
            'updated_at': plan.updated_at or plan.created_at,
        })
    return jsonify(result)


@admin_bp.route("/api/admin/safety-plans/missing")
@role_required('admin')
def get_patients_missing_plans():
    """Patients with chat windows but no active safety plan."""
    patients_with_windows = db.session.query(ChatWindow.patient_id).distinct().all()
    patient_ids = [p[0] for p in patients_with_windows]

    result = []
    for pid in patient_ids:
        active = SafetyPlan.get_active_plan(pid)
        if not active:
            patient = User.query.get(pid)
            assignment = ProviderPatient.query.filter_by(patient_id=pid).first()
            provider = User.query.get(assignment.provider_id) if assignment else None
            window_count = ChatWindow.query.filter_by(patient_id=pid, visible=True).count()
            result.append({
                'patient_id': pid,
                'patient_name': patient.username if patient else 'Unknown',
                'provider_name': provider.username if provider else 'Unassigned',
                'window_count': window_count,
            })
    return jsonify(result)


@admin_bp.route("/api/admin/safety-plans/conflicts")
@role_required('admin')
def get_plan_conflicts():
    """Anti-pattern conflicts in active safety plans."""
    active_plans = SafetyPlan.query.filter_by(status='active').all()
    result = []
    for plan in active_plans:
        prompt_dict = plan.to_prompt_dict()
        conflicts = prompt_dict.get('conflicts', [])
        if conflicts:
            patient = User.query.get(plan.patient_id)
            result.append({
                'plan_id': plan.id,
                'patient_id': plan.patient_id,
                'patient_name': patient.username if patient else 'Unknown',
                'conflict_count': len(conflicts),
                'conflicts': conflicts,
            })
    return jsonify(result)


# ── Audit log ──────────────────────────────────────────────────

@admin_bp.route("/api/admin/audit-log")
@role_required('admin')
def get_audit_log():
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    entries = AuditLog.query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return jsonify([e.to_dict() for e in entries])


# ── Escalation events ─────────────────────────────────────────

@admin_bp.route("/api/admin/escalation-events")
@role_required('admin')
def get_escalation_events():
    status_filter = request.args.get('status')
    query = EscalationEvent.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    events = query.order_by(
        db.case(
            (EscalationEvent.severity == 'critical', 0),
            (EscalationEvent.severity == 'warning', 1),
            else_=2,
        ),
        EscalationEvent.created_at.desc(),
    ).all()
    return jsonify([e.to_dict() for e in events])


@admin_bp.route("/api/admin/escalation-events/<int:event_id>/acknowledge", methods=['POST'])
@role_required('admin')
def acknowledge_escalation(event_id):
    event = EscalationEvent.query.get_or_404(event_id)
    data = request.json or {}
    new_status = data.get('status', 'acknowledged')
    event.status = new_status
    if new_status == 'acknowledged':
        event.acknowledged_by = current_user.id
        event.acknowledged_at = time.time()
    _log_action('escalation_acknowledged', 'escalation_event', event_id, {'status': new_status})
    db.session.commit()
    return jsonify({'status': 'success'})


# ── System flags API (for frontend enforcement) ───────────────

@admin_bp.route("/api/settings/flags")
@role_required('admin')
def get_settings_flags():
    """All global feature flags as a flat dict — used by admin settings tab."""
    return jsonify({
        'providers_can_set_custom_prompts': _get_admin_setting('providers_can_set_custom_prompts', True),
        'users_can_save_selections': _get_admin_setting('users_can_save_selections', True),
        'require_safety_plan': _get_admin_setting('require_safety_plan', True),
        'allow_patient_anti_patterns': _get_admin_setting('allow_patient_anti_patterns', True),
    })
