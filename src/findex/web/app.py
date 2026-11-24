"""FastAPI boundary for the immutable search index."""
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from time import monotonic, perf_counter
from typing import Annotated, Literal, cast
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from findex.index import Index
from findex.ranking import BM25, Searcher, TfIdf, snippet
from findex.query import parse, positive_terms
from findex.store import load

logger = logging.getLogger(__name__)
ScorerName = Literal["bm25", "tfidf"]
HERE = Path(__file__).parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    index_path: Path = Path("data/index.json")
    corpus_path: Path = Path("data/python_docs")
    search_mode: Literal["sync", "async"] = "sync"


class Result(BaseModel):
    doc_id: int
    title: str
    score: float
    snippet: str


class SearchResponse(BaseModel):
    query: str
    total: int
    took_ms: float
    results: list[Result]


class DocumentResponse(BaseModel):
    doc_id: int
    title: str
    path: str
    text: str


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_index(request: Request) -> Index | None:
    return cast(Index | None, request.app.state.index)


def require_index(index: Index | None) -> Index:
    if index is None:
        raise HTTPException(503, "Index not loaded")
    return index


IndexDep = Annotated[Index | None, Depends(get_index)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
QueryText = Annotated[str, Query(min_length=1, max_length=500)]
PageSize = Annotated[int, Query(ge=1, le=100)]
PageNumber = Annotated[int, Query(ge=1, le=1000)]


def read_document(index: Index, settings: Settings, doc_id: int) -> DocumentResponse:
    meta = index.doc_meta.get(doc_id)
    if meta is None:
        raise HTTPException(404, "Unknown document")
    root = settings.corpus_path.resolve()
    path = (root / meta.path).resolve()
    text = ""
    if path.is_relative_to(root) and path.is_file():
        text = path.read_text(encoding="utf-8")
    return DocumentResponse(doc_id=doc_id, title=meta.title, path=meta.path, text=text)


def execute_search(index: Index, settings: Settings, q: str, k: int, scorer: ScorerName, page: int) -> SearchResponse:
    start = perf_counter()
    try:
        searcher = Searcher(index)
        total = len(searcher.ids(q))
        terms = positive_terms(parse(q))
        ranked = searcher.search(q, BM25() if scorer == "bm25" else TfIdf(), min(total, page * k))
        results = []
        for result in ranked[(page - 1) * k:page * k]:
            doc = read_document(index, settings, result.doc_id)
            results.append(Result(doc_id=result.doc_id, title=result.title, score=result.score,
                                  snippet=snippet(doc.text, terms)))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    return SearchResponse(query=q, total=total, took_ms=(perf_counter() - start) * 1000, results=results)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    app.state.settings = settings
    app.state.started = monotonic()
    app.state.index = None
    try:
        app.state.index = load(settings.index_path)
    except (OSError, ValueError):
        logger.exception("Index unavailable")
    yield
    app.state.index = None


def create_app(mode: Literal["sync", "async"] | None = None) -> FastAPI:
    service = FastAPI(title="Findex", version="0.7.0", lifespan=lifespan)
    service.state.index = None
    service.state.settings = Settings()
    service.state.started = monotonic()
    templates = Jinja2Templates(directory=str(HERE / "templates"))
    service.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

    @service.middleware("http")
    async def request_id(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        identifier = uuid4().hex
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_id=%s unexpected error", identifier)
            response = JSONResponse({"detail": "Internal server error"}, status_code=500)
        response.headers["X-Request-ID"] = identifier
        return response

    def sync_search(index: IndexDep, settings: SettingsDep, q: QueryText, k: PageSize = 10,
                    scorer: ScorerName = "bm25", page: PageNumber = 1) -> SearchResponse:
        return execute_search(require_index(index), settings, q, k, scorer, page)

    async def async_search(index: IndexDep, settings: SettingsDep, q: QueryText, k: PageSize = 10,
                           scorer: ScorerName = "bm25", page: PageNumber = 1) -> SearchResponse:
        return execute_search(require_index(index), settings, q, k, scorer, page)

    service.add_api_route("/search", async_search if (mode or Settings().search_mode) == "async" else sync_search,
                          methods=["GET"], response_model=SearchResponse)

    @service.get("/health")
    def health(index: IndexDep) -> dict[str, str]:
        require_index(index)
        return {"status": "ok"}

    @service.get("/stats")
    def stats(index: IndexDep, settings: SettingsDep, request: Request) -> dict[str, int | float]:
        ix = require_index(index)
        return {"documents": ix.num_docs, "vocabulary": len(ix),
                "index_bytes": settings.index_path.stat().st_size if settings.index_path.is_file() else 0,
                "uptime": monotonic() - cast(float, request.app.state.started)}

    @service.get("/docs/{doc_id}")
    def document(doc_id: int, index: IndexDep, settings: SettingsDep) -> DocumentResponse:
        return read_document(require_index(index), settings, doc_id)

    @service.get("/", response_class=HTMLResponse)
    def home(request: Request, index: IndexDep, settings: SettingsDep,
             q: Annotated[str, Query(max_length=500)] = "", page: PageNumber = 1) -> Response:
        result = execute_search(require_index(index), settings, q, 10, "bm25", page) if q else None
        return templates.TemplateResponse(request=request, name="search.html",
            context={"result": result, "q": q, "page": page})

    @service.get("/doc/{doc_id}", response_class=HTMLResponse)
    def document_view(request: Request, doc_id: int, index: IndexDep, settings: SettingsDep) -> Response:
        return templates.TemplateResponse(request=request, name="document.html",
            context={"doc": read_document(require_index(index), settings, doc_id)})

    return service


app = create_app()
