import requests

API_URL = "http://127.0.0.1:8508"
REGISTER_ENDPOINT = f"{API_URL}/auth/register"


def test_register_success():
    """Register a new user should return 201 Created."""
    payload = {"user": "newUser123", "pass": "password"}
    response = requests.post(REGISTER_ENDPOINT, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "message" in data
    assert data["message"].lower().startswith("user created")
    assert data["user"] == "newUser123"


def test_register_missing_fields():
    """Missing password should return 400."""
    payload = {"user": "incompleteUser"}
    response = requests.post(REGISTER_ENDPOINT, json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "missing" in data["error"].lower()


def test_register_existing_user():
    """Registering an existing user should return 409 Conflict."""
    payload = {"user": "existingUser", "pass": "password"}
    response = requests.post(REGISTER_ENDPOINT, json=payload)
    assert response.status_code == 409
    data = response.json()
    assert "exists" in data["error"].lower()

