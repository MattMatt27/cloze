"""M5d cutover checks: old report UI is gone from served pages, new entry
points are present, and the admin ops endpoints work."""
import pytest

from llm_chat.services.report_jobs import enqueue_report, run_once
from tests.test_component_access import _make_admin


@pytest.fixture(autouse=True)
def _fake_llm(monkeypatch):
    monkeypatch.setenv("CLOZE_FAKE_LLM", "1")
    monkeypatch.delenv("REPORTS_WORKER_MODE", raising=False)


def test_provider_chats_page_stripped(study, login_as):
    page = login_as(study.provider1).get(
        "/provider/chat-windows").get_data(as_text=True)
    assert "reportConfigModal" not in page
    assert "reportSettingsWrapper" not in page
    assert 'data-tab="reports"' not in page          # tab removed
    assert "/api/reports/window" not in page         # no old generation calls
    assert "Reports hub" in page                     # pointer to the new home
    assert "/api/v2/reports?scope=window" in page    # deep-link join


def test_patient_reports_page_on_v2(study, login_as):
    page = login_as(study.alice).get("/my-reports").get_data(as_text=True)
    assert "/api/v2/reports" in page
    assert "/api/reports/" not in page.replace("/api/v2/reports", "")
    assert "Reports shared with you" in page


def test_no_served_page_calls_legacy_generation(study, login_as):
    """No page-level UI should reference the legacy generate endpoints."""
    provider_pages = ["/provider/chat-windows", "/provider/dashboard",
                      "/provider/reports"]
    client = login_as(study.provider1)
    for url in provider_pages:
        page = client.get(url).get_data(as_text=True)
        assert "generate-unified" not in page, url
        assert "/api/reports/window" not in page, url


def test_admin_jobs_endpoint(study, login_as):
    enqueue_report("window", study.w1.id)
    run_once()
    admin = login_as(_make_admin())
    jobs = admin.get("/api/v2/admin/report-jobs").get_json()
    assert len(jobs) == 1 and jobs[0]["status"] == "done"
    assert admin.get("/api/v2/admin/report-jobs?status=failed").get_json() == []
    # providers cannot see the ops view
    assert login_as(study.provider1).get(
        "/api/v2/admin/report-jobs").status_code == 403


def test_admin_dashboard_has_report_panels(study, login_as):
    page = login_as(_make_admin()).get("/admin/dashboard").get_data(as_text=True)
    assert "componentGrantsPanel" in page
    assert "reportJobsPanel" in page
    assert "Report Analysis Access" in page