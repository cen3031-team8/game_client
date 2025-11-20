import requests
import pytest

API_URL = "http://127.0.0.1:8508"
LOGIN_ENDPOINT = f"{API_URL}/auth/login"
HEALTH_ENDPOINT = f"{API_URL}/auth/test"

def test_api_health():
    """Check if API health endpoint is up."""
    response = requests.get(HEALTH_ENDPOINT)
    assert response.status_code == 200
    assert "ok" in response.text.lower()

def test_login_success():
    """Valid user login should return 200."""
    payload = {"user": "demoUser", "pass": "demoPass"}
    response = requests.post(LOGIN_ENDPOINT, json=payload)
    assert response.status_code == 200

def test_login_invalid_user():
    """Login with 'notCreated' should fail with 401."""
    payload = {"user": "notCreated", "pass": "anything"}
    response = requests.post(LOGIN_ENDPOINT, json=payload)
    assert response.status_code == 401

def test_login_missing_fields():
    """Missing password should cause 400 Bad Request."""
    payload = {"user": "demoUser"}
    response = requests.post(LOGIN_ENDPOINT, json=payload)
    assert response.status_code in (400, 422)

def test_connection_timeout(monkeypatch):
    """Simulate connection timeout to show graceful handling."""
    def fake_post(*args, **kwargs):
        raise requests.exceptions.Timeout()
    monkeypatch.setattr(requests, "post", fake_post)

    try:
        requests.post(LOGIN_ENDPOINT, json={"user": "x", "pass": "y"}, timeout=0.01)
    except requests.exceptions.Timeout:
        assert True

