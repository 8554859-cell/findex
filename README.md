# findex — Лабораторна робота №3

Студент: Аркан Арсеній Станіславович, Б-122-23-1-ТП.
Навчальна реалізація за допомогою ШІ. [Методичка](https://github.com/rmalkevy/Programming-Practice-Projects/blob/main/courses/python/lab-03-the-object-model-and-ranking.md).

Попередні версії: [Lab 01](../lab-01), [Lab 02](../lab-02).

## Мета
Модель об'єктів Python, протоколи, ранжування, рекурсивний парсер, декоратори.

## Запуск
```sh
uv sync
uv run python scripts/download_python_docs.py
uv run python -m findex.index data/python_docs --out positional.bin --positions
uv run python -m findex.search positional.bin 'python AND (async OR await) NOT java' --scorer bm25 --corpus data/python_docs
uv run python -m findex.search positional.bin '"event loop"' --scorer tfidf --corpus data/python_docs
uv run pytest -q
uv run ruff check .
```

## Реалізація
Index реалізує спеціальні методи контейнера, cached_property для середньої довжини, df та контекстний менеджер open_index у store.py. Позиції токенів опційні; для фраз потрібно створювати індекс з --positions. Старі файли без позицій читаються.
Scorer — структурний протокол; TF-IDF використовує логарифмічну TF, BM25 — насичення TF і нормалізацію довжини. heapq.nlargest обмежує результати до k.
Парсер: NOT має найвищий пріоритет, AND (у тому числі неявний) — середній, OR — найнижчий. Вузли підтримують &, |, ~. Фраза перевіряє послідовні позиції.
timed використовує wraps; Searcher.ids кешує результати запиту, а search друкує cache hit. Сніпет виділяє терміни зірочками навколо найбільш насиченого збігами фрагмента.

## Перевірка
Автоматичні тести та Ruff запускаються у GitHub Actions. Три експерименти ранжування і таблиця precision@5 ще потребують підтверджених результатів; не позначено як завершені.
