import subprocess
from pathlib import Path

import pytest

from scripts import tasks

EXPECTED_TASKS = ('run', 'dashboard', 'seed', 'eval', 'test', 'lint', 'typecheck')
RUNTIME_READY_COMMAND = (
    "from src.config import get_settings; "
    "print('runtime ready:', get_settings().groq_base_url)"
)
EXPECTED_COMMANDS = {
    'run': (
        (
            'uv',
            'run',
            'python',
            '-c',
            RUNTIME_READY_COMMAND,
        ),
    ),
    'seed': (
        ('uv', 'run', 'python', 'scripts/build_dataset.py'),
        ('uv', 'run', 'python', 'scripts/seed_vectordb.py'),
    ),
    'eval': (
        ('uv', 'run', 'python', 'scripts/evaluate_classifier.py'),
    ),
    'test': (('uv', 'run', 'pytest', '-q'),),
    'lint': (('uv', 'run', 'ruff', 'check', '.'),),
    'typecheck': (('uv', 'run', 'mypy', 'src'),),
}



def test_task_runner_exposes_expected_command_names() -> None:
    assert tasks.TASK_NAMES == EXPECTED_TASKS



def test_makefile_uses_task_runner(repo_root: Path) -> None:
    content = (repo_root / 'Makefile').read_text(encoding='utf-8')

    for task_name in EXPECTED_TASKS:
        assert f'uv run python scripts/tasks.py {task_name}' in content


@pytest.mark.parametrize(('task_name', 'commands'), EXPECTED_COMMANDS.items())
def test_task_runner_resolves_expected_commands(
    task_name: str, commands: tuple[tuple[str, ...], ...]
) -> None:
    assert tasks.get_task_commands(task_name) == commands



def test_run_task_dispatches_commands_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[tuple[str, ...], bool, Path]] = []

    def fake_run(command: tuple[str, ...], *, check: bool, cwd: Path) -> None:
        calls.append((command, check, cwd))

    monkeypatch.setattr(tasks.subprocess, 'run', fake_run)

    assert tasks.run_task('seed') == 0
    assert calls == [
        (EXPECTED_COMMANDS['seed'][0], True, tasks.REPO_ROOT),
        (EXPECTED_COMMANDS['seed'][1], True, tasks.REPO_ROOT),
    ]



def test_main_returns_subprocess_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_task(_: str) -> int:
        raise subprocess.CalledProcessError(7, ('uv', 'run', 'pytest', '-q'))

    monkeypatch.setattr(tasks, 'run_task', fake_run_task)

    assert tasks.main(['test']) == 7



def test_get_task_commands_rejects_unknown_task_name() -> None:
    with pytest.raises(ValueError, match='Unsupported task: unknown'):
        tasks.get_task_commands('unknown')



def test_main_rejects_unknown_subcommand() -> None:
    with pytest.raises(SystemExit) as error:
        tasks.main(['unknown'])

    assert error.value.code == 2
