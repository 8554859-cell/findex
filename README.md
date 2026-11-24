# findex — Лабораторна робота №5

Студент: Аркан Арсеній Станіславович, Б-122-23-1-ТП.
Навчальна реалізація за допомогою ШІ. [Методичка](https://github.com/rmalkevy/Programming-Practice-Projects/blob/main/courses/python/lab-05-concurrency-and-the-gil.md).

[![CI](https://github.com/8554859-cell/findex/actions/workflows/lab01.yml/badge.svg)](https://github.com/8554859-cell/findex/actions/workflows/lab01.yml)

## Запуск
```sh
uv sync --locked
uv run python scripts/download_python_docs.py
uv run findex index data/python_docs --out index.bin --positions --workers 4 --executor processes
uv run findex search index.bin "python" --corpus data/python_docs
uv run pytest
uv run python scripts/benchmark_lab05.py data/python_docs
```

## Архітектура
build_partial читає лише передані шляхи, використовує локальні Counter та списки, а merge об'єднує часткові індекси у порядку діапазонів ID. Spawn створює незалежні процеси; future.result передає винятки. Послідовний режим лишається типовим до вимірювання.

## Експеримент
Три незалежні запуски кожної конфігурації; медіана wall, сума CPU часу батьківського процесу та завершених дочірніх процесів, peak RSS лише батьківського процесу, окремий час merge. Linux ru_maxrss у KiB. Python 3.13 та 3.13t використовують один корпус. Результати та PNG ще очікують підтвердження CI.

Попередні лабораторні доступні за тегами lab-01 — lab-04. [Wheel Lab 4](https://github.com/8554859-cell/findex/releases/tag/v0.4.0).
