import httpx
import pytest

from app.config import ENV_FILE, Settings
from app.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_health_returns_public_service_status() -> None:
    application = create_app(Settings(app_env="test"))
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Zero-Touch CLM API",
        "environment": "test",
    }


def test_environment_file_path_is_repository_root() -> None:
    assert ENV_FILE.name == ".env"
    assert (ENV_FILE.parent / "apps" / "backend" / "app" / "config.py").is_file()
