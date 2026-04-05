from pathlib import Path

from src.config import Settings, get_settings


def test_config_import_returns_settings() -> None:
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.request_timeout_seconds == 45.0


def test_phase_one_package_layout_exists(repo_root: Path) -> None:
    expected = [
        repo_root / 'src' / 'llm',
        repo_root / 'src' / 'agents',
        repo_root / 'src' / 'graph',
        repo_root / 'src' / 'tools',
        repo_root / 'scripts',
        repo_root / 'tests',
    ]
    assert all(path.exists() for path in expected)
