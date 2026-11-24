# findex — Лабораторна робота №2

Студент: Аркан Арсеній Станіславович, Б-122-23-1-ТП.

Навчальна реалізація за допомогою ШІ. [Методичка](https://github.com/rmalkevy/Programming-Practice-Projects/blob/main/courses/python/lab-02-data-structures-and-the-inverted-index.md).
[Лабораторна №1](https://github.com/8554859-cell/findex/tree/lab-01).

## Мета та корпус
Інвертований індекс документів зі стандартної бібліотеки Python (той самий корпус, що у Lab 01).

## Запуск
```sh
uv sync
uv run python scripts/download_python_docs.py
uv run python -m findex.index data/python_docs --out index.bin
uv run python -m findex.search index.bin "python OR module" --engine merge
uv run python -m findex.index data/python_docs --out index.json
uv run python -m findex.search index.json "python NOT class" --engine set
uv run pytest -q
uv run ruff check .
uv run python scripts/benchmark_lab02.py
```

## M1–M4
Індекс будується за один прохід; Counter рахує частоти поточного документа, defaultdict накопичує впорядковані постінги. Posting і DocMeta незмінні, зі slots. Зберігаються довжини документів. Позиції не реалізовані (опційна вимога).
Пошук використовує двовказівникові AND/OR/NOT або множини; оператори обчислюються зліва направо, NOT доповнює наступний термін, пробіл означає AND.
Збереження: pickle та JSON. Не відкривайте чужі pickle-файли — можливе виконання довільного коду.
Бенчмарк порівнює plain dataclass, slots і array('I') на одному корпусі. Slots прибирає словник атрибутів; array зберігає числа без окремих об'єктів. Для форматів вимірюються розмір, час запису і читання; для merge/set — середній час AND за 100 повторів.

## Результати
Числа ще не підтверджені. Бенчмарк запускається в GitHub Actions; журнал містить фактичні результати.
Питання захисту: DEFENSE_LAB02.md.
