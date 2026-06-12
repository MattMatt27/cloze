"""Tests for the login flow: success, generic failure (no account
enumeration), account lockout, IP rate limiting, and logout gating."""


def _login(client, username, password):
    return client.post("/api/login", json={"username": username, "password": password})


def test_login_page_renders(client):
    assert client.get("/login").status_code == 200


def test_successful_login_returns_role_and_redirect(client, make_user):
    make_user("prov", role="provider", password="pw-12345")
    resp = _login(client, "prov", "pw-12345")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "success"
    assert body["role"] == "provider"
    assert "redirect" in body


def test_wrong_password_is_generic_401(client, make_user):
    make_user("prov", role="provider", password="pw-12345")
    resp = _login(client, "prov", "nope")
    assert resp.status_code == 401
    assert resp.get_json()["message"] == "Invalid credentials"


def test_unknown_user_response_matches_wrong_password(client, make_user):
    """No account enumeration: an unknown username and a wrong password for a
    real user must be indistinguishable (same status + message)."""
    make_user("real", role="user", password="pw-12345")
    unknown = _login(client, "ghost", "whatever")
    wrong = _login(client, "real", "whatever")
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.get_json() == wrong.get_json()


def test_account_locks_after_five_failures(client, make_user):
    make_user("victim", role="user", password="pw-12345")
    for _ in range(5):
        assert _login(client, "victim", "bad").status_code == 401
    # 6th attempt: account is now locked even though it's under the IP rate cap
    locked = _login(client, "victim", "bad")
    assert locked.status_code == 423


def test_ip_rate_limit_after_ten_attempts(client, make_user):
    # Unknown user avoids per-account lockout so we isolate the IP limiter.
    for _ in range(10):
        assert _login(client, "ghost", "bad").status_code == 401
    assert _login(client, "ghost", "bad").status_code == 429


def test_logout_requires_authentication(client):
    resp = client.get("/logout")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
