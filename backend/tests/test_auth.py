"""Tests for authentication and authorization"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.security import ALGORITHM, SECRET_KEY, create_access_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def valid_access_token():
    """Create a valid access token for testing"""
    token_data = {
        "user_id": "test-user-id",
        "email": "test@example.com",
        "role": "author",
    }
    return create_access_token(token_data)


def test_auth_me_without_auth(client):
    """Test /auth/me endpoint without authentication"""
    response = client.get("/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    # Error format includes error_code
    json_response = response.json()
    assert "Not authenticated" in str(json_response)


@pytest.mark.skip(
    reason="Requires database connection; skipping in CI environment without PostgreSQL"
)
@patch("app.routers.auth.get_db")
def test_auth_me_with_bearer_token(mock_db, client, valid_access_token):
    """Test /auth/me endpoint with Bearer token authentication"""
    # Mock database session and user
    mock_session = MagicMock()
    mock_db.return_value.__aenter__.return_value = mock_session

    # Mock user query result
    mock_user = MagicMock()
    mock_user.id = "test-user-id"
    mock_user.email = "test@example.com"
    mock_user.name = "Test User"
    mock_user.picture = "https://example.com/picture.jpg"
    mock_user.role = "author"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    # Make request with Bearer token
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {valid_access_token}"})

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == "test-user-id"
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert data["role"] == "author"


@pytest.mark.skip(
    reason="Requires database connection; skipping in CI environment without PostgreSQL"
)
def test_auth_me_with_cookie(client, valid_access_token):
    """Test /auth/me endpoint with cookie authentication"""
    with patch("app.routers.auth.get_db") as mock_db:
        # Mock database session and user
        mock_session = MagicMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        # Mock user query result
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.picture = "https://example.com/picture.jpg"
        mock_user.role = "author"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        # Make request with cookie
        response = client.get("/auth/me", cookies={"access_token": valid_access_token})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "test-user-id"
        assert data["email"] == "test@example.com"


def test_get_current_user_with_invalid_token(client):
    """Test authentication with invalid token"""
    invalid_token = "invalid.token.here"
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {invalid_token}"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    # Error format includes error_code
    json_response = response.json()
    assert "Could not validate credentials" in str(json_response)


def test_get_current_user_with_expired_token(client):
    """Test authentication with expired token"""
    from datetime import datetime, timedelta

    # Create an expired token
    expired_data = {
        "user_id": "test-user-id",
        "exp": datetime.utcnow() - timedelta(hours=1),
        "type": "access",
    }
    expired_token = jwt.encode(expired_data, SECRET_KEY, algorithm=ALGORITHM)

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_logout_endpoint(client):
    """Test logout endpoint clears cookies"""
    response = client.post("/auth/logout")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Logged out successfully"

    # Check that cookies are cleared
    for cookie in response.cookies.values():
        if cookie.key in ["access_token", "refresh_token"]:
            assert cookie.value == '""'  # Cookie should be cleared


@pytest.mark.skip(
    reason="Requires database connection; skipping in CI environment without PostgreSQL"
)
@patch("app.routers.auth.exchange_code_for_token")
@patch("app.routers.auth.validate_oauth_state")
@patch("app.routers.auth.get_db")
def test_google_callback_creates_new_user(mock_db, mock_validate, mock_exchange, client):
    """Test Google OAuth callback creates new user"""
    # Mock OAuth state validation
    mock_validate.return_value = "mock-verifier"

    # Mock token exchange
    mock_exchange.return_value = (
        {"access_token": "google-token"},
        {
            "sub": "google-sub-123",
            "email": "newuser@example.com",
            "name": "New User",
            "picture": "https://example.com/pic.jpg",
        },
    )

    # Mock database session
    mock_session = MagicMock()
    mock_db.return_value.__aenter__.return_value = mock_session

    # Mock user not found (new user)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    # Mock the new user object that gets created
    mock_new_user = MagicMock()
    mock_new_user.id = "new-user-id"
    mock_new_user.email = "newuser@example.com"
    mock_new_user.role = "author"

    # Mock refresh to return the new user
    def refresh_side_effect(user):
        user.id = "new-user-id"
        user.email = "newuser@example.com"
        user.role = "author"

    mock_session.refresh.side_effect = refresh_side_effect

    # Make callback request
    response = client.get("/auth/callback/google?code=test-code&state=test-state")

    # Should redirect to frontend
    assert response.status_code == status.HTTP_302_FOUND
    assert response.headers["location"] in ["http://localhost:3000", "https://sopher.ai"]

    # Verify user was added to session
    assert mock_session.add.called


@patch("app.routers.auth.validate_oauth_state")
def test_google_callback_invalid_state(mock_validate, client):
    """Test Google OAuth callback with invalid state"""
    # Mock invalid state
    mock_validate.return_value = None

    response = client.get("/auth/callback/google?code=test-code&state=invalid-state")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    # Error format includes error_code
    json_response = response.json()
    assert "Invalid or expired state parameter" in str(json_response)
