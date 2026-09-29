from fastapi.testclient import TestClient

from app.main import app

PASSWORD = "Forecast#2026"
EMAIL = "analyst@example.com"


def _login(client: TestClient) -> str:
    response = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_health_and_forecast_flow():
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["latest_init"] == "2026-09-27"

        denied = client.get("/api/forecasts/blended")
        assert denied.status_code == 401

        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        blended = client.get(
            "/api/forecasts/blended",
            params={"variable": "rainfall", "lead_hour": 24, "region": "india"},
            headers=headers,
        )
        assert blended.status_code == 200, blended.text
        body = blended.json()
        assert body["type"] == "FeatureCollection"
        assert len(body["features"]) == 100
        assert "weights" in body["features"][0]["properties"]

        models = client.get("/api/forecasts/models", headers=headers)
        assert models.status_code == 200
        assert len(models.json()["models"]) == 5

        weights = client.get(
            "/api/weights/maps",
            params={"variable": "tmax", "lead_hour": 72, "season": "JJAS"},
            headers=headers,
        )
        assert weights.status_code == 200
        assert weights.json()["legend"]

        skill = client.get("/api/metrics/skill", params={"variable": "rainfall"}, headers=headers)
        assert skill.status_code == 200
        assert skill.json()["improvement_pct_vs_best_corrected"] > 0
        assert skill.json()["scorecard_rows"] > 0

        extremes = client.get(
            "/api/extremes",
            params={"hazard": "heavy_rain", "lead_hour": 48},
            headers=headers,
        )
        assert extremes.status_code == 200
        assert extremes.json()["summary"]["cells"] == 100

        overview = client.get("/api/extremes/overview", headers=headers)
        assert overview.status_code == 200
        assert "heat_wave" in overview.json()["hazards"]

        series = client.get(
            "/api/forecasts/series",
            params={"variable": "wind_speed", "lat": 22, "lon": 78},
            headers=headers,
        )
        assert series.status_code == 200
        assert len(series.json()["blend"]) == 8

        jobs = client.get("/api/jobs", headers=headers)
        assert jobs.status_code == 200
        assert jobs.json()["jobs"]

        me = client.get("/api/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == EMAIL


def test_register_and_refresh():
    with TestClient(app) as client:
        created = client.post(
            "/api/auth/register",
            json={"email": "new.analyst@example.com", "password": "another-pass", "full_name": "New Analyst"},
        )
        assert created.status_code == 200, created.text
        refreshed = client.post("/api/auth/refresh", json={"refresh_token": created.json()["refresh_token"]})
        assert refreshed.status_code == 200
        duplicate = client.post(
            "/api/auth/register",
            json={"email": "new.analyst@example.com", "password": "another-pass"},
        )
        assert duplicate.status_code == 409
