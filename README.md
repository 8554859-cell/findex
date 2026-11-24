# findex — Лабораторна робота №7

**Публічна адреса:** [https://findex-9t0d.onrender.com](https://findex-9t0d.onrender.com)

Студент: Аркан Арсеній Станіславович, Б-122-23-1-ТП. Навчальна реалізація за допомогою ШІ.

[Методичка](https://github.com/rmalkevy/Programming-Practice-Projects/blob/main/courses/python/lab-07-fastapi-web-search.md)

## Запуск
```sh
uv sync
uv run python scripts/download_python_docs.py
uv run findex index data/python_docs --out data/index.json --positions
uv run findex serve --port 8000
```
Відкрити http://127.0.0.1:8000/ або /docs для OpenAPI.

## API
/search — q, k, scorer, page; /docs/{id}; /stats; /health (503 без індексу).
Налаштування INDEX_PATH, CORPUS_PATH, SEARCH_MODE через environment або .env. Індекс завантажується один раз на процес у lifespan. Pydantic використовується на межі API; залежності підміняються у тестах.

## Docker та розгортання
```sh
docker build -t findex .
docker run --rm -p 8000:8000 findex
```
Render Blueprint: render.yaml, Docker, healthCheckPath /health. Сервіс розгорнуто на безкоштовному Render (Oregon), Docker, 0.1 CPU, 512 MB RAM. Health check: /health. Публічний пошук та HTML перевірено через CI; запит python повернув 394 збіги. Безкоштовний інстанс може засинати. Журнали доступні в Render Dashboard.

## Експерименти
Фактичний [успішний запуск GitHub Actions](https://github.com/8554859-cell/findex/actions/runs/45473618791): 45 тестів, 82% покриття, Pyright і Ruff без помилок, Docker smoke та публічний HTTP тест успішні. Корпус — 8013 фрагментів документації Python.

### 20 одночасних запитів (ASGITransport)

| Режим | Wall, с | RPS | p50, мс | p95, мс | p99, мс |
|---|---:|---:|---:|---:|---:|
| async def | 0.1896 | 105.46 | 127.74 | 131.27 | 188.72 |
| def | 0.1836 | 108.93 | 174.12 | 180.02 | 180.64 |

### oha (HTTP, /search?q=python%20OR%20module&k=10)

| Target | Concurrency | Requests | RPS | p50, ms | p95, ms | p99, ms |
|---|---:|---:|---:|---:|---:|---:|
| local, 1 worker, async def | 50 | 300 | 169.00 | 294.561 | 399.740 | 460.862 |
| local, 1 worker, def | 50 | 300 | 115.54 | 433.065 | 470.172 | 489.698 |
| local, 4 workers, def | 50 | 300 | 215.98 | 258.380 | 316.583 | 343.391 |
| Render, def | 20 | 100 | 12.05 | 1702.267 | 2301.035 | 2394.100 |

Усі 1000 запитів успішні. Сирий JSON публічного тесту — артефакт lab07-public-oha у зазначеному CI. Чотири процеси дали 1.87× RPS відносно одного sync-воркера. Async варіант швидший за sync в локальному HTTP тесті, але синхронні обчислення та читання файлів усередині async def блокують event loop. Тому залишено def: це захищає чутливість інших маршрутів, хоча thread pool додає витрати і не усуває GIL. Render має інші ресурси та мережеву затримку, тому його RPS не можна прямо порівнювати з локальним.  CPU-пошук у async def може заблокувати event loop; sync def переносить його в thread pool, але GIL обмежує CPU-паралельність. Кілька воркерів — окремі процеси з власним індексом, що збільшує використання пам'яті.
