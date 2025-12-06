"""Скрипт сборки пакета Support Hints Agent System."""

from pathlib import Path
from setuptools import find_packages, setup

from typing import List


def read_requirements() -> List[str]:
    """Загружает список зависимостей из requirements.txt, если он существует.

    Returns:
        List[str]: Упорядоченный список зависимостей без комментариев и пустых строк.
    """
    req_path = Path(__file__).parent / "requirements.txt"
    if req_path.exists():
        return [line.strip() for line in req_path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")]
    return []


setup(
    name="support-agent-system",
    version="0.1.0",
    description="Support hints agent system API (RAG + agents)",
    packages=find_packages(exclude=("*.ipynb", "notebooks", "tests")),
    include_package_data=True,
    install_requires=read_requirements(),
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "support-hints-api=main:serve",
        ]
    },
)
