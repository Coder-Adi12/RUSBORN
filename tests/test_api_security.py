from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app


def test_internal_endpoint_rejects_missing_secret() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/appointments/availability",
            json={
                "date": "2099-01-05",
                "time": "10:00",
                "timezone": "Asia/Kolkata",
            },
        )

    assert response.status_code == 401


def test_dashboard_rejects_anonymous_request() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard/stats")

    assert response.status_code == 401


def test_dashboard_login_creates_session_for_protected_routes() -> None:
    with patch("api.routers.dashboard.get_dashboard_stats", return_value={"ok": True}):
        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={"username": "operator", "password": "test-dashboard-password"},
            )
            response = client.get("/api/v1/dashboard/stats")

    assert login.status_code == 200
    assert response.status_code == 200
    assert response.json() == {"ok": True}
