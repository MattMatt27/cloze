"""Full-page report viewer — the addressable document at /reports/<id>.

Shared by providers (hub chrome, regenerate, downloads) and participants
(minimal chrome, only template-shared reports). Drill-down links resolve
against actual child Report rows and the caller's read rights — the renderer
itself never decides visibility.
"""

import json

from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from report.renderers.v2_document import SCOPE_LABELS, render_document

from ..extensions import db
from ..models import Report
from .reports_v2 import _can_read_report

report_pages_bp = Blueprint("report_pages", __name__)


def _child_report_links(report_data):
    """{group_key: viewer_url} for groups whose child report exists and is
    readable by the current user."""
    prefix_to_scope = {"window": "window", "flow": "flow",
                       "enrollment": "enrollment"}
    links = {}
    for group in report_data.get("groups", []):
        key = group.get("key", "")
        prefix, _, raw_id = key.partition(":")
        scope = prefix_to_scope.get(prefix)
        if scope is None or not raw_id.isdigit():
            continue
        from ..services.report_jobs import SCOPE_FK
        child = Report.query.filter_by(
            scope=scope, report_type="v2", **{SCOPE_FK[scope]: int(raw_id)}
        ).first()
        if child is not None and _can_read_report(child):
            links[key] = f"/reports/{child.id}"
    return links


@report_pages_bp.route("/reports/<int:report_id>")
@login_required
def view_report(report_id):
    report = db.session.get(Report, report_id)
    if report is None or report.report_type != "v2":
        abort(404)
    if not _can_read_report(report):
        abort(403)

    report_data = json.loads(report.report_data) if report.report_data else {}
    document_html = render_document(report_data, links=_child_report_links(report_data))

    from ..services.artifacts import ANALYZER_VERSION
    from ..services.report_jobs import SCOPE_FK
    return render_template(
        "report_view.html",
        report=report,
        scope=report.effective_scope,
        scope_id=getattr(report, SCOPE_FK[report.effective_scope]),
        scope_label=SCOPE_LABELS.get(report.effective_scope, "Report"),
        document_html=document_html,
        is_stale=(report.analyzer_version is not None
                  and report.analyzer_version != ANALYZER_VERSION),
        can_manage=(current_user.is_admin()
                    or (current_user.is_provider()
                        and report.provider_id == current_user.id)),
    )
