"""Tiered component access: everything visible, standard free, intensive
gated by admin grants; request→grant flow; enforcement at template save AND
generation; system-template semantics."""
import json

import pytest

from llm_chat.extensions import db as _db
from llm_chat.models import Report, ReportTemplate
from llm_chat.services.component_access import (
    component_access,
    pending_requests,
    set_grant,
    usable_components,
)
from llm_chat.services.report_jobs import enqueue_report, run_once
from report.registry_v2 import COMPONENTS

INTENSIVE = {k for k, c in COMPONENTS.items() if c.cost == "intensive"}
STANDARD = set(COMPONENTS) - INTENSIVE


@pytest.fixture(autouse=True)
def _fake_llm(monkeypatch):
    monkeypatch.setenv("CLOZE_FAKE_LLM", "1")
    monkeypatch.delenv("REPORTS_WORKER_MODE", raising=False)


def _post(client, url, body):
    return client.post(url, data=json.dumps(body), content_type="application/json")


def test_registry_costs():
    """LLM components are the intensive tier today; the rest are free."""
    assert INTENSIVE == {"ai_summary", "hierarchical_summary"}


def test_default_access_and_usable(study):
    access = component_access(study.provider1.id)
    assert all(access[k] == "available" for k in STANDARD)
    assert all(access[k] == "requestable" for k in INTENSIVE)
    assert usable_components(study.provider1.id) == STANDARD


def test_request_then_grant_flow(study, login_as):
    provider_client = login_as(study.provider1)
    response = _post(provider_client, "/api/v2/reports/component-requests",
                     {"component": "hierarchical_summary"})
    assert response.status_code == 202
    assert response.get_json()["state"] == "requested"
    assert ("hierarchical_summary" not in
            usable_components(study.provider1.id))
    assert (study.provider1.id, "hierarchical_summary") in pending_requests()

    admin = login_as(_make_admin())
    queue = admin.get("/api/v2/admin/component-grants").get_json()
    assert {"provider_id": study.provider1.id,
            "component": "hierarchical_summary"} in queue["pending"]

    response = admin.put("/api/v2/admin/component-grants",
                         data=json.dumps({"provider_id": study.provider1.id,
                                          "component": "hierarchical_summary",
                                          "granted": True}),
                         content_type="application/json")
    assert response.status_code == 200
    assert "hierarchical_summary" in usable_components(study.provider1.id)
    assert pending_requests() == []

    # revoke clears it entirely
    set_grant(study.provider1.id, "hierarchical_summary", False)
    assert component_access(study.provider1.id)["hierarchical_summary"] == "requestable"


def test_request_validation(study, login_as):
    client = login_as(study.provider1)
    assert _post(client, "/api/v2/reports/component-requests",
                 {"component": "descriptive_stats"}).status_code == 400  # standard
    assert _post(client, "/api/v2/reports/component-requests",
                 {"component": "nope"}).status_code == 400
    # participants/admins can't request
    assert _post(login_as(study.alice), "/api/v2/reports/component-requests",
                 {"component": "hierarchical_summary"}).status_code == 403


def test_grants_endpoints_admin_only(study, login_as):
    client = login_as(study.provider1)
    assert client.get("/api/v2/admin/component-grants").status_code == 403
    assert client.put("/api/v2/admin/component-grants",
                      data=json.dumps({"provider_id": 1, "component": "x",
                                       "granted": True}),
                      content_type="application/json").status_code == 403


def test_template_save_rejects_ungranted_intensive(study, login_as):
    client = login_as(study.provider1)
    response = _post(client, "/api/v2/report-templates",
                     {"name": "With summaries", "scope": "window",
                      "components": ["descriptive_stats", "hierarchical_summary"]})
    assert response.status_code == 403  # body is the app's HTML 403 page

    set_grant(study.provider1.id, "hierarchical_summary", True)
    client = login_as(study.provider1)
    assert _post(client, "/api/v2/report-templates",
                 {"name": "With summaries", "scope": "window",
                  "components": ["descriptive_stats", "hierarchical_summary"]}
                 ).status_code == 201


def test_generation_filters_by_grant(study):
    """Defense in depth: even a template listing an intensive component only
    yields it when the team currently holds the grant."""
    enqueue_report("window", study.w1.id)
    run_once()
    report = Report.query.filter_by(report_type="v2").one()
    sections = json.loads(report.report_data)["sections"]
    assert "hierarchical_summary" not in sections  # no grant
    assert "descriptive_stats" in sections

    set_grant(study.provider1.id, "hierarchical_summary", True)
    enqueue_report("window", study.w1.id)
    run_once()
    report = Report.query.filter_by(report_type="v2").one()
    sections = json.loads(report.report_data)["sections"]
    assert "hierarchical_summary" in sections  # granted → present after regen


def test_registry_endpoint_reports_access_state(study, login_as):
    set_grant(study.provider1.id, "ai_summary", True)
    payload = login_as(study.provider1).get("/api/v2/reports/registry").get_json()
    by_key = {c["key"]: c for c in payload["components"]}
    assert by_key["descriptive_stats"]["access"] == "available"
    assert by_key["ai_summary"]["access"] == "granted"
    assert by_key["hierarchical_summary"]["access"] == "requestable"
    assert by_key["hierarchical_summary"]["cost"] == "intensive"


def test_system_templates_usable_not_editable(study, login_as):
    admin_user = _make_admin()
    system = ReportTemplate(name="Weekly phase report", scope="window",
                            created_by=admin_user.id)
    _db.session.add(system)
    _db.session.commit()

    client = login_as(study.provider1)
    listing = client.get("/api/v2/report-templates").get_json()
    mine = {t["name"]: t for t in listing}
    assert mine["Weekly phase report"]["is_system"] is True

    # usable for generation…
    response = _post(client, "/api/v2/reports/jobs",
                     {"scope": "window", "scope_id": study.w1.id,
                      "template_id": system.id})
    assert response.status_code == 202
    # …but not editable or deletable by providers
    assert client.put(f"/api/v2/report-templates/{system.id}",
                      data=json.dumps({"name": "mine now"}),
                      content_type="application/json").status_code == 403
    assert client.delete(f"/api/v2/report-templates/{system.id}",
                         content_type="application/json").status_code == 403


def test_participant_visible_scope_rule(study, login_as):
    client = login_as(study.provider1)
    # flow/account scopes can never be participant-visible
    for scope in ("flow", "account", "participant"):
        response = _post(client, "/api/v2/report-templates",
                         {"name": "leak", "scope": scope,
                          "participant_visible": True})
        assert response.status_code == 400, scope
    # window/enrollment/conversation can
    assert _post(client, "/api/v2/report-templates",
                 {"name": "ok", "scope": "enrollment",
                  "participant_visible": True}).status_code == 201
    # and flipping scope later can't smuggle visibility through
    template = _post(client, "/api/v2/report-templates",
                     {"name": "w", "scope": "window",
                      "participant_visible": True}).get_json()
    assert client.put(f"/api/v2/report-templates/{template['id']}",
                      data=json.dumps({"scope": "flow"}),
                      content_type="application/json").status_code == 400


def _make_admin():
    from llm_chat.models import User
    admin = User.query.filter_by(role="admin").first()
    if admin is None:
        admin = User(username="admin1", email="admin1@example.test", role="admin")
        admin.set_password("pw-12345")
        _db.session.add(admin)
        _db.session.commit()
    return admin