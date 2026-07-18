"""Hub surface: navigator tree, hub page access, provider nav entry."""
import pytest


@pytest.fixture(autouse=True)
def _fake_llm(monkeypatch):
    monkeypatch.setenv("CLOZE_FAKE_LLM", "1")
    monkeypatch.delenv("REPORTS_WORKER_MODE", raising=False)


def test_navigator_tree_shape(study, login_as):
    tree = login_as(study.provider1).get("/api/v2/reports/navigator").get_json()
    assert tree["provider_id"] == study.provider1.id

    assert [f["name"] for f in tree["flows"]] == ["Mindfulness"]
    flow = tree["flows"][0]
    assert [e["username"] for e in flow["enrollments"]] == ["alice", "bob"]

    alice_node = flow["enrollments"][0]
    assert alice_node["enrollment_id"] == study.enr_alice.id
    # both FK-linked and legacy name-linked windows, start-date ordered
    assert [w["title"] for w in alice_node["windows"]] == ["Week 1", "Week 2"]

    assert {p["username"] for p in tree["participants"]} == {"alice", "bob"}


def test_navigator_isolated_per_provider(study, login_as):
    tree = login_as(study.provider2).get("/api/v2/reports/navigator").get_json()
    assert [f["name"] for f in tree["flows"]] == ["Other Study"]
    assert {p["username"] for p in tree["participants"]} == {"carol"}


def test_navigator_roles(study, login_as):
    assert login_as(study.alice).get(
        "/api/v2/reports/navigator").status_code == 403
    # admin must specify which provider's tree
    from tests.test_component_access import _make_admin
    admin = login_as(_make_admin())
    assert admin.get("/api/v2/reports/navigator").status_code == 400
    tree = admin.get(
        f"/api/v2/reports/navigator?provider_id={study.provider1.id}").get_json()
    assert tree["provider_id"] == study.provider1.id


def test_hub_page_access(study, login_as):
    response = login_as(study.provider1).get("/provider/reports")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "scopeNav" in page and "Templates" in page
    assert "/static/js/reports/hub.js" in page

    assert login_as(study.alice).get("/provider/reports").status_code == 403


def test_provider_nav_has_reports_link(study, login_as):
    page = login_as(study.provider1).get(
        "/provider/reports").get_data(as_text=True)
    assert 'href="/provider/reports"' in page  # nav item present