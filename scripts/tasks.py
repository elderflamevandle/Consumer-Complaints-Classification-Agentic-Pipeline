"""Cross-platform task runner for baseline repository operations."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Sequence

Command = tuple[str, ...]
CommandGroup = tuple[Command, ...]

REPO_ROOT = Path(__file__).resolve().parents[1]

TASK_COMMANDS: dict[str, CommandGroup] = {
    'run': (
        (
            'uv',
            'run',
            'python',
            '-c',
            "from src.config import get_settings; print('runtime ready:', get_settings().groq_base_url)",
        ),
    ),
    'seed': (
        ('uv', 'run', 'python', 'scripts/build_dataset.py'),
        ('uv', 'run', 'python', 'scripts/seed_vectordb.py'),
    ),
    'eval': (
        ('uv', 'run', 'python', '-c', "print('Evaluation harness arrives in Phase 6.')"),
    ),
    'test': (('uv', 'run', 'pytest', '-q'),),
    'lint': (('uv', 'run', 'ruff', 'check', '.'),),
    'typecheck': (('uv', 'run', 'mypy', 'src'),),
}
TASK_NAMES = tuple(TASK_COMMANDS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Run baseline repository tasks from a cross-platform Python CLI.'
    )
    parser.add_argument('task', choices=TASK_NAMES, help='Task to execute')
    return parser


def get_task_commands(task_name: str) -> CommandGroup:
    try:
        return TASK_COMMANDS[task_name]
    except KeyError as error:
        raise ValueError(f'Unsupported task: {task_name}') from error


def run_task(task_name: str) -> int:
    for command in get_task_commands(task_name):
        subprocess.run(command, check=True, cwd=REPO_ROOT)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return run_task(args.task)
    except subprocess.CalledProcessError as error:
        return error.returncode


if __name__ == '__main__':
    raise SystemExit(main())
