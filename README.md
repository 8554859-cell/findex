# findex — Лабораторна робота №4

Студент: Аркан Арсеній Станіславович, Б-122-23-1-ТП.
Навчальна реалізація за допомогою ШІ. [Методичка](https://github.com/rmalkevy/Programming-Practice-Projects/blob/main/courses/python/lab-04-typing-testing-packaging-cli.md).

[![CI](https://github.com/8554859-cell/findex/actions/workflows/lab01.yml/badge.svg)](https://github.com/8554859-cell/findex/actions/workflows/lab01.yml)

## Запуск
```sh
uv sync
uv run python scripts/download_python_docs.py
uv tool install .
findex index data/python_docs --out index.json --positions
findex search index.json "python OR module" --corpus data/python_docs
findex search index.json "python" --json
findex stats index.json
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest --cov=findex --cov-report=term-missing
uv build
```

CLI використовує Typer і Rich; JSON-рядки спрямовуються у stdout, логування — stderr. Для діагностики використовуйте -v або -vv перед підкомандою. Pickle відкривайте лише з довірених джерел.

## Перевірка
Результати CI, покриття, lock-файл та публікація wheel ще не підтверджені. Попередні лабораторні збережені тегами lab-01 — lab-03.
