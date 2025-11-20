import requests

API_URL = "http://127.0.0.1:8508"
PROFILE_ENDPOINT = f"{API_URL}/auth/profile"
VERSION_ENDPOINT = f"{API_URL}/auth/version"


def test_profile_unauthorized():
    """GET /auth/profile without a valid token should return 401."""
    response = requests.get(PROFILE_ENDPOINT)
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"].lower() == "unauthorized"


def test_profile_authorized():
    """GET /auth/profile with valid token should return 200 and user data."""
    headers = {"Authorization": "Bearer valid_demo_token"}
    response = requests.get(PROFILE_ENDPOINT, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user"] == "demoUser"
    assert data["role"] == "trainer"


def test_api_version():
    """GET /auth/version should return version and status info."""
    response = requests.get(VERSION_ENDPOINT)
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert data["version"] == "1.0.0"
    assert data["status"].lower() == "stable"

