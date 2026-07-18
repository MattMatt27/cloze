"""Report system v2 HTTP surface: /api/v2/reports* and /api/v2/report-templates*.

Access model (design doc):
- admin: everything
- provider: only scopes they own (scope_owner: window/flow ownership,
  ProviderPatient linkage, account = self)
- participant: read-only, only reports on their own data whose template is
  participant_visible; participants never enqueue generation

Generation is asynchronous: POST /reports/jobs returns 202 with the job row;
the client polls GET /reports/jobs/<id> until done (report_id set). Rendered
document/download endpoints land with the UI milestone.
"""

import json

from flask import Blueprint, abort, jsonify, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Report, ReportJob, ReportTemplate, StudyFlow
from ..services.report_jobs import SCOPE_FK, enqueue_report
from ..services.scopes import (
    SCOPES,
    ScopeNotFoundError,
    UnknownScopeError,
    scope_owner,
)
from report.registry_v2 import COMPONENTS

reports_v2_bp = Blueprint("reports_v2", __name__, url_prefix="/api/v2")


# --- access helpers -----------------------------------------------------------

def _check_scope_access(scope, scope_id, *, for_generation=False):
    """Abort 400/403/404 unless current_user may touch this scope target."""
    try:
        provider_id, patient_id = scope_owner(scope, scope_id)
    except UnknownScopeError:
        abort(400, description="unknown scope")
    except ScopeNotFoundError:
        abort(404)

    if current_user.is_admin():
        return provider_id, patient_id
    if current_user.is_provider():
        if provider_id == current_user.id:
            return provider_id, patient_id
        abort(403)
    # participants never generate, and their read access is per-report
    # (template visibility), checked in _can_read_report
    abort(403)


def _can_read_report(report):
    if current_user.is_admin():
        return True
    if current_user.is_provider():
        return report.provider_id == current_user.id
    if current_user.is_patient():
        if report.patient_id != current_user.id:
            return False
        if report.template_id is None:
            return False  # untemplated reports are research artifacts
        template = db.session.get(ReportTemplate, report.template_id)
        return bool(template and template.participant_visible)
    return False


def _serialize_report(report, include_data=False):
    from ..services.artifacts import ANALYZER_VERSION
    payload = {
        "id": report.id,
        "scope": report.effective_scope,
        "scope_id": getattr(report, SCOPE_FK[report.effective_scope]),
        "report_type": report.report_type,
        "template_id": report.template_id,
        "provider_id": report.provider_id,
        "patient_id": report.patient_id,
        "generated_at": report.generated_at,
        "analyzer_version": report.analyzer_version,
        "is_stale": (report.analyzer_version is not None
                     and report.analyzer_version != ANALYZER_VERSION),
    }
    if include_data:
        payload["report_data"] = (
            json.loads(report.report_data) if report.report_data else {}
        )
    return payload


# --- jobs ---------------------------------------------------------------------

@reports_v2_bp.route("/reports/jobs", methods=["POST"])
@login_required
def create_report_job():
    if not (current_user.is_provider() or current_user.is_admin()):
        abort(403)
    body = request.get_json(silent=True) or {}
    scope = body.get("scope")
    scope_id = body.get("scope_id")
    if scope not in SCOPES or not isinstance(scope_id, int):
        abort(400, description="scope (one of %s) and integer scope_id required"
              % ", ".join(SCOPES))
    _check_scope_access(scope, scope_id, for_generation=True)

    template_id = body.get("template_id")
    if template_id is not None:
        template = db.session.get(ReportTemplate, template_id)
        if template is None:
            abort(404, description="template not found")
        _check_template_access(template)
        if template.scope != scope:
            abort(400, description="template scope %r does not match %r"
                  % (template.scope, scope))

    job = enqueue_report(scope, scope_id, requested_by=current_user.id,
                         template_id=template_id)
    return jsonify(job.to_dict()), 202


@reports_v2_bp.route("/reports/jobs/<int:job_id>", methods=["GET"])
@login_required
def get_report_job(job_id):
    job = db.session.get(ReportJob, job_id)
    if job is None:
        abort(404)
    if not current_user.is_admin():
        if not current_user.is_provider():
            abort(403)
        if job.scope is None or getattr(job, SCOPE_FK[job.scope]) is None:
            abort(403)
        _check_scope_access(job.scope, getattr(job, SCOPE_FK[job.scope]))
    return jsonify(job.to_dict())


# --- reports ------------------------------------------------------------------

@reports_v2_bp.route("/reports", methods=["GET"])
@login_required
def list_reports():
    scope = request.args.get("scope")
    query = Report.query.filter_by(report_type="v2")

    if scope is not None:
        if scope not in SCOPES:
            abort(400, description="unknown scope")
        query = query.filter_by(scope=scope)
        scope_id = request.args.get("scope_id", type=int)
        if scope_id is not None:
            query = query.filter_by(**{SCOPE_FK[scope]: scope_id})

    if current_user.is_admin():
        pass
    elif current_user.is_provider():
        query = query.filter_by(provider_id=current_user.id)
    else:
        # participants: own data + participant_visible template, via join
        query = (query.filter_by(patient_id=current_user.id)
                 .join(ReportTemplate, Report.template_id == ReportTemplate.id)
                 .filter(ReportTemplate.participant_visible.is_(True)))

    reports = query.order_by(Report.generated_at.desc()).all()
    return jsonify([_serialize_report(r) for r in reports])


@reports_v2_bp.route("/reports/<int:report_id>", methods=["GET"])
@login_required
def get_report(report_id):
    report = db.session.get(Report, report_id)
    if report is None or report.report_type != "v2":
        abort(404)
    if not _can_read_report(report):
        abort(403)
    return jsonify(_serialize_report(report, include_data=True))


@reports_v2_bp.route("/reports/registry", methods=["GET"])
@login_required
def get_registry():
    return jsonify({
        "scopes": list(SCOPES),
        "components": [
            {"key": c.key, "label": c.label, "scopes": sorted(c.scopes)}
            for c in COMPONENTS.values()
        ],
    })


# --- templates ----------------------------------------------------------------

def _check_template_access(template):
    if current_user.is_admin():
        return
    if not current_user.is_provider():
        abort(403)
    if template.flow_id is not None:
        flow = db.session.get(StudyFlow, template.flow_id)
        if flow is None or flow.provider_id != current_user.id:
            abort(403)
    elif template.created_by != current_user.id:
        abort(403)


def _validated_template_fields(body, *, partial=False):
    fields = {}
    if not partial or "name" in body:
        name = (body.get("name") or "").strip()
        if not name:
            abort(400, description="name required")
        fields["name"] = name
    if not partial or "scope" in body:
        scope = body.get("scope")
        if scope not in SCOPES:
            abort(400, description="scope must be one of %s" % ", ".join(SCOPES))
        fields["scope"] = scope
    if "components" in body:
        components = body.get("components")
        if components is not None:
            if (not isinstance(components, list)
                    or not all(isinstance(k, str) for k in components)):
                abort(400, description="components must be a list of keys")
            unknown = [k for k in components if k not in COMPONENTS]
            if unknown:
                abort(400, description="unknown components: %s" % ", ".join(unknown))
        fields["components"] = json.dumps(components) if components else None
    if "flow_id" in body:
        flow_id = body.get("flow_id")
        if flow_id is not None:
            flow = db.session.get(StudyFlow, flow_id)
            if flow is None:
                abort(404, description="flow not found")
            if not current_user.is_admin() and flow.provider_id != current_user.id:
                abort(403)
        fields["flow_id"] = flow_id
    for flag in ("auto_generate", "participant_visible"):
        if flag in body:
            if not isinstance(body[flag], bool):
                abort(400, description=f"{flag} must be boolean")
            fields[flag] = body[flag]
    return fields


@reports_v2_bp.route("/report-templates", methods=["GET"])
@login_required
def list_templates():
    if current_user.is_admin():
        templates = ReportTemplate.query.all()
    elif current_user.is_provider():
        own_flows = db.session.query(StudyFlow.id).filter_by(
            provider_id=current_user.id)
        templates = ReportTemplate.query.filter(
            (ReportTemplate.created_by == current_user.id)
            | (ReportTemplate.flow_id.in_(own_flows))
        ).all()
    else:
        abort(403)
    return jsonify([t.to_dict() for t in templates])


@reports_v2_bp.route("/report-templates", methods=["POST"])
@login_required
def create_template():
    if not (current_user.is_provider() or current_user.is_admin()):
        abort(403)
    body = request.get_json(silent=True) or {}
    fields = _validated_template_fields(body)
    template = ReportTemplate(created_by=current_user.id, **fields)
    db.session.add(template)
    db.session.commit()
    return jsonify(template.to_dict()), 201


@reports_v2_bp.route("/report-templates/<int:template_id>", methods=["PUT"])
@login_required
def update_template(template_id):
    template = db.session.get(ReportTemplate, template_id)
    if template is None:
        abort(404)
    _check_template_access(template)
    body = request.get_json(silent=True) or {}
    for key, value in _validated_template_fields(body, partial=True).items():
        setattr(template, key, value)
    db.session.commit()
    return jsonify(template.to_dict())


@reports_v2_bp.route("/report-templates/<int:template_id>", methods=["DELETE"])
@login_required
def delete_template(template_id):
    template = db.session.get(ReportTemplate, template_id)
    if template is None:
        abort(404)
    _check_template_access(template)
    db.session.delete(template)
    db.session.commit()
    return jsonify({"deleted": template_id})
