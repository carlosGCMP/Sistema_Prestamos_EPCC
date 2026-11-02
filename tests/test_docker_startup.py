import subprocess
from pathlib import Path
from unittest.mock import Mock, call

import pytest

from scripts import iniciar


def test_find_docker_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(iniciar.shutil, "which", lambda _name: "C:/Docker/docker.exe")
    assert iniciar.find_docker() == "C:/Docker/docker.exe"


def test_find_docker_desktop_without_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    program_files = tmp_path / "Program Files"
    executable = program_files / "Docker/Docker/resources/bin/docker.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    monkeypatch.setattr(iniciar.shutil, "which", lambda _name: None)
    monkeypatch.setattr(iniciar.sys, "platform", "win32")
    monkeypatch.setenv("ProgramFiles", str(program_files))
    assert iniciar.find_docker() == str(executable)


def test_missing_docker_has_actionable_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(iniciar.shutil, "which", lambda _name: None)
    monkeypatch.setattr(iniciar.sys, "platform", "win32")
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    with pytest.raises(iniciar.StartupError, match="Instala Docker Desktop"):
        iniciar.find_docker()


@pytest.mark.parametrize(
    "error",
    [subprocess.CalledProcessError(1, "docker"), subprocess.TimeoutExpired("docker", 20)],
)
def test_docker_not_ready_explains_desktop_and_wsl(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    monkeypatch.setattr(iniciar, "run", Mock(side_effect=error))
    with pytest.raises(iniciar.StartupError, match="Docker Desktop.*WSL 2"):
        iniciar.check_docker("docker.exe")


def test_windows_container_engine_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = Mock(return_value=subprocess.CompletedProcess([], 0, stdout="windows\n"))
    monkeypatch.setattr(iniciar, "run", runner)
    with pytest.raises(iniciar.StartupError, match="Switch to Linux containers"):
        iniciar.check_docker("docker.exe")
    runner.assert_called_once()


@pytest.mark.parametrize("help_text", ["--wait", "--wait-timeout", "up options"])
def test_old_compose_is_rejected(monkeypatch: pytest.MonkeyPatch, help_text: str) -> None:
    runner = Mock(
        side_effect=[
            subprocess.CompletedProcess([], 0, stdout="linux\n"),
            subprocess.CompletedProcess([], 0, stdout=help_text),
        ]
    )
    monkeypatch.setattr(iniciar, "run", runner)
    with pytest.raises(iniciar.StartupError, match="demasiado antiguo"):
        iniciar.check_docker("docker.exe")


def test_missing_compose_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = Mock(
        side_effect=[
            subprocess.CompletedProcess([], 0, stdout="linux\n"),
            subprocess.CalledProcessError(1, "docker compose"),
        ]
    )
    monkeypatch.setattr(iniciar, "run", runner)
    with pytest.raises(iniciar.StartupError, match="Compose no está disponible"):
        iniciar.check_docker("docker.exe")


def test_linux_engine_and_supported_compose_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = Mock(
        side_effect=[
            subprocess.CompletedProcess([], 0, stdout="linux\n"),
            subprocess.CompletedProcess([], 0, stdout="--wait --wait-timeout"),
        ]
    )
    monkeypatch.setattr(iniciar, "run", runner)
    iniciar.check_docker("docker.exe")
    assert runner.call_count == 2


def test_compose_uses_explicit_file_and_waits_for_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "Proyecto con espacios"
    runner = Mock()
    monkeypatch.setattr(iniciar, "ROOT", root)
    monkeypatch.setattr(iniciar, "run", runner)
    iniciar.start_database("C:/Program Files/Docker/docker.exe")
    prefix = (
        "C:/Program Files/Docker/docker.exe",
        "compose",
        "--file",
        str(root / "docker-compose.yml"),
    )
    assert runner.call_args_list == [
        call(*prefix, "config", "--quiet", timeout=20),
        call(*prefix, "up", "-d", "--wait", "--wait-timeout", "90", "db", timeout=None),
    ]


def test_database_failure_does_not_delete_data(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = Mock(side_effect=[None, subprocess.CalledProcessError(1, "docker compose up")])
    monkeypatch.setattr(iniciar, "compose", runner)
    with pytest.raises(iniciar.StartupError, match="(?s)puerto 5433.*No borres"):
        iniciar.start_database("docker.exe")
    assert runner.call_count == 2


def test_docker_only_does_not_prepare_application(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(iniciar.sys, "argv", ["iniciar.py", "--docker-only"])
    monkeypatch.setattr(iniciar, "find_docker", lambda: "docker.exe")
    check = Mock()
    start = Mock()
    monkeypatch.setattr(iniciar, "check_docker", check)
    monkeypatch.setattr(iniciar, "start_database", start)
    monkeypatch.setattr(iniciar, "prepare_env", Mock(side_effect=AssertionError("Modificó .env")))
    monkeypatch.setattr(iniciar, "run", Mock(side_effect=AssertionError("Ejecutó la aplicación")))
    monkeypatch.setattr(iniciar.venv, "EnvBuilder", Mock(side_effect=AssertionError("Creó .venv")))
    iniciar.main()
    check.assert_called_once_with("docker.exe")
    start.assert_called_once_with("docker.exe")


def test_docker_failure_stops_before_creating_files(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(iniciar.sys, "argv", ["iniciar.py"])
    monkeypatch.setattr(iniciar, "find_docker", lambda: "docker.exe")
    monkeypatch.setattr(
        iniciar, "check_docker", Mock(side_effect=iniciar.StartupError("Motor apagado"))
    )
    monkeypatch.setattr(iniciar, "prepare_env", Mock(side_effect=AssertionError("Modificó .env")))
    with pytest.raises(iniciar.StartupError, match="Motor apagado"):
        iniciar.main()
