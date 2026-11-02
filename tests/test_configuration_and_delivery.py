import importlib
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from app.core.settings import Settings
from app.infrastructure import database
from scripts.iniciar import prepare_env


def test_default_postgresql_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(_env_file=None)
    url = make_url(settings.database_url)
    assert url.get_backend_name() == "postgresql"
    assert url.port == 5433


def test_legacy_connection_shares_engine_without_connecting(capsys: pytest.CaptureFixture) -> None:
    with patch.object(
        database.engine, "connect", side_effect=AssertionError("Conexión al importar")
    ):
        legacy = importlib.import_module("app.conexion_python_base_datos")
        importlib.reload(legacy)
    assert legacy.motor_base_datos is database.engine
    assert legacy.BaseDatos is database.Base
    assert legacy.SesionBaseDatos is database.SessionLocal
    assert legacy.obtener_conexion is database.get_session
    assert not capsys.readouterr().out


def test_env_creation_generates_secret_and_preserves_existing(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    (tmp_path / ".env.example").write_text((root / ".env.example").read_text(encoding="utf-8"))
    prepare_env(tmp_path)
    content = (tmp_path / ".env").read_text()
    assert "localhost:5433/epcc_prestamos" in content
    assert "replace-with" not in content
    assert len(next(line for line in content.splitlines() if line.startswith("JWT_SECRET="))) > 43
    prepare_env(tmp_path)
    assert (tmp_path / ".env").read_text() == content


def test_readiness_checks_database_and_handles_failure(client: TestClient) -> None:
    main = importlib.import_module("app.main")
    engine = create_engine("sqlite://")
    try:
        with patch.object(main, "engine", engine):
            assert client.get("/health/ready").json() == {"status": "ready"}
            with patch.object(engine, "connect", side_effect=OperationalError("", {}, Exception())):
                response = client.get("/health/ready")
            assert response.status_code == 503
            assert response.json() == {"detail": "Base de datos no disponible"}
    finally:
        engine.dispose()


def test_frontend_assets_are_served(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="login-form"' in response.text
    for path in ("/app.js", "/styles.css"):
        assert client.get(path).status_code == 200
