"""/api/v2 surface: job lifecycle over HTTP, scope access control,
participant visibility via templates, templates CRUD, auto-generation."""
import json

import pytest

from llm_chat.extensions import db as _db
from llm_chat.models import Report, ReportTemplate
from llm_chat.services.report_jobs import run_auto_generation, run_once


@pytest.fixture(autouse=True)
def _fake_llm(monkeypatch):
    monkeypatch.setenv("CLOZE_FAKE_LLM", "1")
    monkeypatch.delenv("REPORTS_WORKER_MODE", raising=False)


def _post(client, url, body):
    return client.post(url, data=json.dumps(body), content_type="application/json")


# --- job lifecycle over HTTP --------------------------------------------------

def test_job_lifecycle_over_http(study, login_as):
    client = login_as(study.provider1)

    response = _post(client, "/api/v2/reports/jobs",
                     {"scope": "window", "scope_id": study.w1.id})
    assert response.status_code == 202
    job = response.get_json()
    assert job["status"] == "queued"

    run_once()  # the worker's turn

    response = client.get(f"/api/v2/reports/jobs/{job['id']}")
    polled = response.get_json()
    assert polled["status"] == "done"
    assert polled["report_id"] is not None

    response = client.get(f"/api/v2/reports/{polled['report_id']}")
    assert response.status_code == 200
    report = response.get_json()
    assert report["scope"] == "window"
    assert report["scope_id"] == study.w1.id
    assert report["is_stale"] is False
    assert "descriptive_stats" in report["report_data"]["sections"]


def test_job_requires_valid_scope_and_target(study, login_as):
    client = login_as(study.provider1)
    assert _post(client, "/api/v2/reports/jobs",
                 {"scope": "galaxy", "scope_id": 1}).status_code == 400
    assert _post(client, "/api/v2/reports/jobs",
                 {"scope": "window"}).status_code == 400
    assert _post(client, "/api/v2/reports/jobs",
                 {"scope": "window", "scope_id": 999999}).status_code == 404


# --- access control -----------------------------------------------------------

def test_provider_cannot_touch_other_providers_scopes(study, login_as):
    client = login_as(study.provider2)
    for scope, scope_id in [
        ("window", study.w1.id),
        ("flow", study.flow1.id),
        ("enrollment", study.enr_alice.id),
        ("participant", study.alice.id),
        ("account", study.provider1.id),
        ("conversation", study.convs["a_w1_1"].id),
    ]:
        response = _post(client, "/api/v2/reports/jobs",
                         {"scope": scope, "scope_id": scope_id})
        assert response.status_code == 403, scope


def test_participant_cannot_enqueue(study, login_as):
    client = login_as(study.alice)
    response = _post(client, "/api/v2/reports/jobs",
                     {"scope": "window", "scope_id": study.w1.id})
    assert response.status_code == 403


def test_report_read_isolation(study, login_as):
    provider_client = login_as(study.provider1)
    _post(provider_client, "/api/v2/reports/jobs",
          {"scope": "window", "scope_id": study.w1.id})
    run_once()
    report_id = Report.query.filter_by(report_type="v2").one().id

    assert login_as(study.provider2).get(
        f"/api/v2/reports/{report_id}").status_code == 403
    # alice's data, but no participant_visible template → hidden
    assert login_as(study.alice).get(
        f"/api/v2/reports/{report_id}").status_code == 403
    assert login_as(study.provider1).get(
        f"/api/v2/reports/{report_id}").status_code == 200


def test_participant_sees_only_templated_visible_reports(study, login_as):
    template = ReportTemplate(name="Weekly participant recap", scope="window",
                              flow_id=study.flow1.id, participant_visible=True,
                              created_by=study.provider1.id)
    _db.session.add(template)
    _db.session.commit()

    provider_client = login_as(study.provider1)
    _post(provider_client, "/api/v2/reports/jobs",
          {"scope": "window", "scope_id": study.w1.id, "template_id": template.id})
    run_once()
    report_id = Report.query.filter_by(report_type="v2").one().id

    alice_client = login_as(study.alice)
    assert alice_client.get(f"/api/v2/reports/{report_id}").status_code == 200
    listing = alice_client.get("/api/v2/reports").get_json()
    assert [r["id"] for r in listing] == [report_id]
    # bob's listing is empty — not his report
    assert login_as(study.bob).get("/api/v2/reports").get_json() == []


def test_listing_filters_by_scope_target(study, login_as):
    client = login_as(study.provider1)
    for scope, scope_id in [("window", study.w1.id), ("flow", study.flow1.id)]:
        _post(client, "/api/v2/reports/jobs", {"scope": scope, "scope_id": scope_id})
        run_once()

    everything = client.get("/api/v2/reports").get_json()
    assert len(everything) == 2
    only_window = client.get(
        f"/api/v2/reports?scope=window&scope_id={study.w1.id}").get_json()
    assert len(only_window) == 1
    assert only_window[0]["scope"] == "window"


def test_registry_endpoint(study, login_as):
    payload = login_as(study.provider1).get("/api/v2/reports/registry").get_json()
    assert set(payload["scopes"]) == {
        "conversation", "window", "enrollment", "participant", "flow", "account"
    }
    by_key = {c["key"]: c for c in payload["components"]}
    assert "account" not in by_key["cooccurrence"]["scopes"]
    assert by_key["engagement_overview"]["scopes"] == ["account"]


# --- templates CRUD -----------------------------------------------------------

def test_template_crud_and_validation(study, login_as):
    client = login_as(study.provider1)

    response = _post(client, "/api/v2/report-templates", {
        "name": "Phase report", "scope": "window", "flow_id": study.flow1.id,
        "components": ["descriptive_stats", "sentiment_analysis"],
        "auto_generate": True,
    })
    assert response.status_code == 201
    template = response.get_json()
    assert template["auto_generate"] is True
    assert template["participant_visible"] is False  # default off

    # validation
    assert _post(client, "/api/v2/report-templates",
                 {"name": "x", "scope": "nope"}).status_code == 400
    assert _post(client, "/api/v2/report-templates",
                 {"name": "x", "scope": "window",
                  "components": ["not_a_component"]}).status_code == 400
    # cannot attach to another provider's flow
    assert _post(client, "/api/v2/report-templates",
                 {"name": "x", "scope": "window",
                  "flow_id": study.flow2.id}).status_code == 403

    # update + ownership
    update = client.put(f"/api/v2/report-templates/{template['id']}",
                        data=json.dumps({"participant_visible": True}),
                        content_type="application/json")
    assert update.status_code == 200
    assert update.get_json()["participant_visible"] is True
    other = login_as(study.provider2)
    assert other.put(f"/api/v2/report-templates/{template['id']}",
                     data=json.dumps({"name": "hijack"}),
                     content_type="application/json").status_code == 403
    assert other.delete(f"/api/v2/report-templates/{template['id']}",
                        content_type="application/json").status_code == 403

    # fresh client: switching identities requires re-login (see login_as note)
    client = login_as(study.provider1)
    assert client.delete(f"/api/v2/report-templates/{template['id']}",
                         content_type="application/json").status_code == 200
    assert ReportTemplate.query.count() == 0


def test_template_scope_must_match_job_scope(study, login_as):
    client = login_as(study.provider1)
    template = _post(client, "/api/v2/report-templates",
                     {"name": "Flow recap", "scope": "flow",
                      "flow_id": study.flow1.id}).get_json()
    response = _post(client, "/api/v2/reports/jobs",
                     {"scope": "window", "scope_id": study.w1.id,
                      "template_id": template["id"]})
    assert response.status_code == 400


def test_template_restricts_components(study, login_as):
    client = login_as(study.provider1)
    template = _post(client, "/api/v2/report-templates",
                     {"name": "Stats only", "scope": "window",
                      "components": ["descriptive_stats"]}).get_json()
    _post(client, "/api/v2/reports/jobs",
          {"scope": "window", "scope_id": study.w1.id,
           "template_id": template["id"]})
    run_once()
    report = Report.query.filter_by(report_type="v2").one()
    data = json.loads(report.report_data)
    assert set(data["sections"]) == {"descriptive_stats"}
    assert report.template_id == template["id"]


# --- auto-generation ----------------------------------------------------------

def test_auto_generation_enqueues_once_per_expired_window(study):
    # w1..w4 all ended in the past (T0-based); template covers flow1 only.
    template = ReportTemplate(name="Auto phase reports", scope="window",
                              flow_id=study.flow1.id, auto_generate=True,
                              created_by=study.provider1.id)
    _db.session.add(template)
    _db.session.commit()

    first = run_auto_generation()
    # flow1 windows: w1 (FK), w2 (legacy name-link), w3 — not w4 (standalone),
    # not w5 (other flow)
    assert len(first) == 3
    assert run_auto_generation() == []  # queued jobs block re-enqueue

    for _ in range(3):
        assert run_once().status == "done"
    assert Report.query.filter_by(report_type="v2").count() == 3
    assert run_auto_generation() == []  # existing reports block re-enqueue

    reports = Report.query.filter_by(report_type="v2").all()
    assert {r.window_id for r in reports} == {study.w1.id, study.w2.id, study.w3.id}
    assert all(r.template_id == template.id for r in reports)


def test_auto_generation_without_templates_is_noop(study):
    assert run_auto_generation() == []