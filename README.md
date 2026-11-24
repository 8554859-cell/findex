# findex — Лабораторна робота №7

**Публічна адреса:** ще не розгорнуто. Потрібен доступ до платформи хостингу.

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
Render Blueprint: render.yaml, Docker, healthCheckPath /health. Обліковий запис хостингу та публічна адреса ще не підтверджені.

## Експерименти
Результати локальних тестів, oha та Docker ще очікують перевірки. CPU-пошук у async def може заблокувати event loop; sync def переносить його в thread pool, але GIL обмежує CPU-паралельність. Кілька воркерів — окремі процеси з власним індексом, що збільшує використання пам'яті.
