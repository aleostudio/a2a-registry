import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app, agent_store, agent_failures

client = TestClient(app)

# Agent card example
VALID_CARD = {
    "name": "Test Agent",
    "description": "A test agent",
    "skills": [
        {
            "name": "translation",
            "description": "Translates text between languages",
            "tags": ["translate", "language", "i18n"],
        }
    ],
}


# Clear stores before each test
def setup_function():
    agent_store.clear()
    agent_failures.clear()


# GET /
################################################################################

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["agents"] == 0
    assert "check_interval" in data


def test_health_check_with_agents():
    agent_store["https://example.com"] = VALID_CARD
    response = client.get("/")
    data = response.json()
    assert data["agents"] == 1


# POST /register
################################################################################

@patch("app.main.httpx.AsyncClient")
def test_register_success(mock_client_cls):
    mock_response = MagicMock()
    mock_response.json.return_value = VALID_CARD
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    response = client.post("/register", json={"url": "https://example.com"})
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "registered"
    assert data["agent"] == "Test Agent"
    assert "https://example.com" in agent_store


def test_register_invalid_url():
    response = client.post("/register", json={"url": "not-a-valid-url"})
    assert response.status_code == 422


@patch("app.main.httpx.AsyncClient")
def test_register_unreachable(mock_client_cls):
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    response = client.post("/register", json={"url": "https://unreachable.example.com"})
    assert response.status_code == 502
    assert "Failed to fetch agent card" in response.json()["detail"]


@patch("app.main.httpx.AsyncClient")
def test_register_invalid_card(mock_client_cls):
    mock_response = MagicMock()
    mock_response.json.return_value = {"invalid": "card"}  # missing "name"
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    response = client.post("/register", json={"url": "https://example.com"})
    assert response.status_code == 422
    assert "Invalid agent card" in response.json()["detail"]


# GET /agents
################################################################################

def test_agents_empty():
    response = client.get("/agents")
    assert response.status_code == 200
    assert response.json() == []


def test_agents_with_data():
    agent_store["https://example.com"] = VALID_CARD

    response = client.get("/agents")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["url"] == "https://example.com"
    assert data[0]["card"]["name"] == "Test Agent"


# GET /discover
################################################################################

def test_discover_match_by_tag():
    agent_store["https://example.com"] = VALID_CARD

    response = client.get("/discover", params={"skill": "translate"})
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["url"] == "https://example.com"


def test_discover_match_by_name():
    agent_store["https://example.com"] = VALID_CARD

    response = client.get("/discover", params={"skill": "translation"})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_discover_match_by_description():
    agent_store["https://example.com"] = VALID_CARD

    response = client.get("/discover", params={"skill": "translates"})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_discover_case_insensitive():
    agent_store["https://example.com"] = VALID_CARD

    response = client.get("/discover", params={"skill": "TRANSLATE"})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_discover_no_match():
    agent_store["https://example.com"] = VALID_CARD

    response = client.get("/discover", params={"skill": "nonexistent"})
    assert response.status_code == 200
    assert response.json() == []


def test_discover_empty_store():
    response = client.get("/discover", params={"skill": "anything"})
    assert response.status_code == 200
    assert response.json() == []


# DELETE /unregister
################################################################################

def test_unregister_success():
    agent_store["https://example.com"] = VALID_CARD
    agent_failures["https://example.com"] = 0

    response = client.delete("/unregister", params={"url": "https://example.com"})
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "unregistered"
    assert data["url"] == "https://example.com"
    assert "https://example.com" not in agent_store
    assert "https://example.com" not in agent_failures


def test_unregister_not_found():
    response = client.delete("/unregister", params={"url": "https://nonexistent.example.com"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found"

