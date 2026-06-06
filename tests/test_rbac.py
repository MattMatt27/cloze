"""Tests for the @role_required decorator and role gating on real routes."""
import pytest
from flask import url_for

from llm_chat.utils.decorators import role_required


@pytest.fixture
def protected_app(app):
    """Register throwaway role-gated routes on the test app."""
    @app.route("/_test/admin-only")
    @role_required("admin")
    def _admin_only():
        return "ok", 200

    @app.route("/_test/staff-only")
    @role_required("admin", "provider")
    def _staff_only():
        return "ok", 200

    return app


def test_unauthenticated_is_redirected_to_login(protected_app, client):
    resp = client.get("/_test/admin-only")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_wrong_role_is_forbidden(protected_app, make_user, login_as):
    c = login_as(make_user("pt", role="user"))
    assert c.get("/_test/admin-only").status_code == 403


def test_correct_role_is_allowed(protected_app, make_user, login_as):
    c = login_as(make_user("admin", role="admin"))
    assert c.get("/_test/admin-only").status_code == 200


def test_multi_role_decorator_admits_each_listed_role(protected_app, make_user, login_as):
    provider_client = login_as(make_user("prov", role="provider"))
    assert provider_client.get("/_test/staff-only").status_code == 200

    patient_client = login_as(make_user("pt", role="user"))
    assert patient_client.get("/_test/staff-only").status_code == 403


def test_real_admin_dashboard_blocks_non_admin(app, make_user, login_as):
    """Integration check: the real admin dashboard rejects a provider."""
    with app.test_request_context():
        path = url_for("admin.admin_dashboard")
    c = login_as(make_user("prov", role="provider"))
    assert c.get(path).status_code == 403
