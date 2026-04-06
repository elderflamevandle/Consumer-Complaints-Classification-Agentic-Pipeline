from pathlib import Path

from scripts import tasks

EXPECTED_TASKS = ('run', 'seed', 'eval', 'test', 'lint', 'typecheck')


def test_task_runner_exposes_expected_command_names() -> None:
    assert tasks.TASK_NAMES == EXPECTED_TASKS


def test_makefile_uses_task_runner(repo_root: Path) -> None:
    content = (repo_root / 'Makefile').read_text(encoding='utf-8')

    for task_name in EXPECTED_TASKS:
        assert f'uv run python scripts/tasks.py {task_name}' in content
