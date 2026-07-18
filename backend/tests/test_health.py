from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_should_return_ok_when_called() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
