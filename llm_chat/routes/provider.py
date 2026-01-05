import json
from flask import Blueprint, render_template, jsonify, request, abort
from flask_login import current_user
from ..utils.decorators import role_required
from ..extensions import db
from ..models import User, Conversation, ProviderPatient, ProviderSettings, ChatWindow

provider_bp = Blueprint("provider", __name__, url_prefix="")

@provider_bp.route("/provider/dashboard")
@role_required('provider', 'admin')
def provider_dashboard():
    return render_template("provider_dashboard.html")

@provider_bp.route("/provider/chat-windows")
@role_required('provider', 'admin')
def provider_chat_windows():
    return render_template("provider_chat_windows.html")

@provider_bp.route("/provider/patient-progress")
@role_required('provider', 'admin')
def provider_patient_progress():
    return render_template("provider_patient_progress.html")

@provider_bp.route("/api/provider/patients")
@role_required('provider', 'admin')
def get_provider_patients():
    if current_user.is_admin():
        patients = User.query.filter_by(role='user').all()
    else:
        patient_ids = [pp.patient_id for pp in current_user.patients]
        patients = User.query.filter(User.id.in_(patient_ids)).all()

    def last_active_for(u: User):
        conv = u.conversations.order_by(Conversation.updated_at.desc()).first()
        return conv.updated_at if conv else None

    def visible_conversation_count(u: User):
        return Conversation.query.join(ChatWindow).filter(
            Conversation.user_id == u.id,
            ChatWindow.visible == True
        ).count()

    return jsonify([{
        'id': p.id,
        'username': p.username,
        'email': p.email,
        'conversation_count': visible_conversation_count(p),
        'last_active': last_active_for(p)
    } for p in patients])

@provider_bp.route("/api/provider/patient/<int:patient_id>/conversations")
@role_required('provider', 'admin')
def get_patient_conversations(patient_id):
    if not current_user.can_access_patient(patient_id):
        abort(403)
    patient = User.query.get_or_404(patient_id)
    conversations = patient.conversations.order_by(Conversation.updated_at.desc()).all()
    return jsonify([{
        'id': c.id,
        'title': c.title or 'Untitled',
        'model': c.model.name,
        'created_at': c.created_at,
        'message_count': c.messages.count()
    } for c in conversations])

@provider_bp.route("/api/provider/settings", methods=['GET', 'POST'])
@role_required('provider', 'admin')
def provider_settings():
    if request.method == 'POST':
        data = request.json or {}
        patient_id = data.get('patient_id')

        if not current_user.can_access_patient(patient_id):
            abort(403)

        settings = ProviderSettings.query.filter_by(
            provider_id=current_user.id, patient_id=patient_id
        ).first()

        if not settings:
            settings = ProviderSettings(provider_id=current_user.id, patient_id=patient_id)
            db.session.add(settings)

        settings.allowed_models = json.dumps(data.get('allowed_models', []))
        settings.system_prompt_id = data.get('system_prompt_id')
        settings.time_window_start = data.get('time_window_start')
        settings.time_window_end = data.get('time_window_end')
        settings.max_messages_per_day = data.get('max_messages_per_day')
        settings.custom_instructions = data.get('custom_instructions')
        db.session.commit()
        return jsonify({'status': 'success'})

    # GET
    patient_id = request.args.get('patient_id')
    settings = ProviderSettings.query.filter_by(
        provider_id=current_user.id, patient_id=patient_id
    ).first()

    if settings:
        return jsonify({
            'allowed_models': json.loads(settings.allowed_models or '[]'),
            'system_prompt_id': settings.system_prompt_id,
            'time_window_start': settings.time_window_start,
            'time_window_end': settings.time_window_end,
            'max_messages_per_day': settings.max_messages_per_day,
            'custom_instructions': settings.custom_instructions
        })
    return jsonify({})
