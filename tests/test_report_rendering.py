"""Renderer + viewer page + download endpoints.

Renderer units run on generated report_data (via the engine with FakeLLM);
route tests exercise access control and the drill-down link resolution."""

import pytest

from llm_chat.models import Report, ReportTemplate
from llm_chat.services.report_jobs import enqueue_report, run_once
from llm_chat.services.scope_engine import generate_report_data
from report.renderers.v2_document import (
    render_csv,
    render_document,
    render_standalone_html,
)


@pytest.fixture(autouse=True)
def _fake_llm(monkeypatch):
    monkeypatch.setenv("CLOZE_FAKE_LLM", "1")
    monkeypatch.delenv("REPORTS_WORKER_MODE", raising=False)


def _generate_v2(scope, scope_id):
    from llm_chat.extensions import db as _db
    enqueue_report(scope, scope_id)
    executed = run_once()
    assert executed.status == "done", executed.error
    return _db.session.get(Report, executed.report_id)


# --- renderer units -----------------------------------------------------------

def test_document_renders_window_sections(study):
    data = generate_report_data("window", study.w1.id)
    html = render_document(data)
    assert "cz-report" in html
    assert "Week 1" in html            # title
    assert "Overview" in html          # descriptive stats section
    assert "Sentiment" in html
    assert "Phase report" in html      # scope label
    assert "<script" not in html       # self-contained, no JS


def test_document_escapes_content(study):
    data = generate_report_data("window", study.w1.id)
    data["title"] = "<script>alert(1)</script>"
    html = render_document(data)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_trend_chart_svg_present(study):
    data = generate_report_data("enrollment", study.enr_alice.id)
    html = render_document(data)
    assert "<svg" in html and "polyline" in html
    assert "Trends over time" in html
    assert "Period comparison" in html


def test_drilldown_links_rendered_when_provided(study):
    data = generate_report_data("enrollment", study.enr_alice.id)
    keys = [g["key"] for g in data["groups"]]
    html = render_document(data, links={keys[0]: "/reports/42"})
    assert 'href="/reports/42"' in html


def test_standalone_html_is_full_document(study):
    data = generate_report_data("window", study.w1.id)
    html = render_standalone_html(data)
    assert html.startswith("<!doctype html>")
    assert "</html>" in html


def test_csv_tables(study):
    data = generate_report_data("enrollment", study.enr_alice.id)
    conversations_csv = render_csv(data)
    lines = conversations_csv.strip().splitlines()
    assert lines[0] == "conversation_id,user_messages,user_words,mean_sentiment,duration_seconds"
    assert len(lines) == 1 + 3  # alice's three flow conversations

    groups_csv = render_csv(data, table="groups")
    assert "Week 1" in groups_csv and "Week 2" in groups_csv

    with pytest.raises(ValueError):
        render_csv(data, table="nope")


# --- viewer page --------------------------------------------------------------

def test_viewer_page_provider(study, login_as):
    report = _generate_v2("window", study.w1.id)
    response = login_as(study.provider1).get(f"/reports/{report.id}")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "cz-report" in page
    assert "Regenerate" in page          # provider chrome
    assert "Reports hub" in page


def test_viewer_page_access(study, login_as):
    report = _generate_v2("window", study.w1.id)
    assert login_as(study.provider2).get(f"/reports/{report.id}").status_code == 403
    assert login_as(study.alice).get(f"/reports/{report.id}").status_code == 403


def test_viewer_page_participant_visible(study, login_as):
    from llm_chat.extensions import db as _db
    template = ReportTemplate(name="Recap", scope="window",
                              participant_visible=True,
                              created_by=study.provider1.id)
    _db.session.add(template)
    _db.session.commit()
    enqueue_report("window", study.w1.id, template_id=template.id)
    executed = run_once()
    response = login_as(study.alice).get(f"/reports/{executed.report_id}")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "My Reports" in page          # participant chrome
    assert "Regenerate" not in page      # no management actions


def test_viewer_drilldown_links_resolve_child_reports(study, login_as):
    child = _generate_v2("window", study.w1.id)
    parent = _generate_v2("enrollment", study.enr_alice.id)
    page = login_as(study.provider1).get(
        f"/reports/{parent.id}").get_data(as_text=True)
    assert f'href="/reports/{child.id}"' in page  # Week 1 has a report
    # Week 2 has no report → its label appears unlinked
    assert "Week 2" in page


# --- downloads ----------------------------------------------------------------

def test_download_html_and_csv(study, login_as):
    report = _generate_v2("window", study.w1.id)
    client = login_as(study.provider1)

    html_response = client.get(f"/api/v2/reports/{report.id}/download/html")
    assert html_response.status_code == 200
    assert "attachment" in html_response.headers["Content-Disposition"]
    assert html_response.get_data(as_text=True).startswith("<!doctype html>")

    csv_response = client.get(f"/api/v2/reports/{report.id}/download/csv")
    assert csv_response.status_code == 200
    assert csv_response.mimetype == "text/csv"
    assert "conversation_id" in csv_response.get_data(as_text=True)

    assert client.get(
        f"/api/v2/reports/{report.id}/download/docx").status_code == 400


def test_download_pdf(study, login_as):
    pytest.importorskip("weasyprint")
    report = _generate_v2("window", study.w1.id)
    response = login_as(study.provider1).get(
        f"/api/v2/reports/{report.id}/download/pdf")
    assert response.status_code == 200
    assert response.data[:5] == b"%PDF-"


def test_download_access_control(study, login_as):
    report = _generate_v2("window", study.w1.id)
    assert login_as(study.provider2).get(
        f"/api/v2/reports/{report.id}/download/html").status_code == 403