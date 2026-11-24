"""Installable command line interface."""

import json
import logging
import pickle
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from findex.index import build_index
from findex.ranking import BM25, Searcher, TfIdf
from findex.store import load, save

app = typer.Typer(no_args_is_help=True)
console = Console()
err = Console(stderr=True)
logger = logging.getLogger(__name__)
ScorerName = Literal["bm25", "tfidf"]


@app.callback()
def configure(
    verbose: Annotated[int, typer.Option("--verbose", "-v", count=True)] = 0,
) -> None:
    logging.basicConfig(
        level=logging.DEBUG
        if verbose >= 2
        else logging.INFO
        if verbose
        else logging.WARNING,
        format="%(levelname)s: %(message)s",
        force=True,
    )


@app.command("index")
def index_command(
    corpus: Path,
    out: Annotated[Path, typer.Option("--out")],
    positions: bool = False,
    limit: Annotated[int | None, typer.Option(min=0)] = None,
) -> None:
    try:
        if not corpus.is_dir():
            raise ValueError("Corpus directory does not exist")
        with Progress(console=err) as progress:
            task = progress.add_task("Building index", total=None)
            index = build_index(corpus, positions, limit)
            save(index, out)
            progress.update(task, total=1, completed=1)
        console.print(f"Indexed {index.num_docs} documents")
    except (OSError, ValueError) as exc:
        logger.error("%s", exc)
        raise typer.Exit(1) from None


@app.command("search")
def search_command(
    index: Path,
    query: str,
    k: Annotated[int, typer.Option(min=1)] = 10,
    scorer: str = "bm25",
    json_output: Annotated[bool, typer.Option("--json")] = False,
    corpus: Path | None = None,
) -> None:
    try:
        if scorer not in ("bm25", "tfidf"):
            raise ValueError("Scorer must be bm25 or tfidf")
        ix = load(index)
        results = Searcher(ix, corpus).search(
            query, BM25() if scorer == "bm25" else TfIdf(), k
        )
        if json_output:
            for result in results:
                typer.echo(json.dumps(asdict(result), ensure_ascii=False))
            return
        table = Table("ID", "Score", "Title", "Snippet")
        for result in results:
            table.add_row(
                str(result.doc_id), f"{result.score:.4f}", result.title, result.snippet
            )
        console.print(table)
    except (OSError, ValueError, EOFError, pickle.UnpicklingError) as exc:
        logger.error("%s", exc)
        raise typer.Exit(1) from None


@app.command("stats")
def stats_command(index: Path) -> None:
    try:
        ix = load(index)
        table = Table("Metric", "Value")
        table.add_row("Documents", str(ix.num_docs))
        table.add_row("Tokens", str(sum(ix.doc_lengths.values())))
        table.add_row("Vocabulary", str(len(ix)))
        for term, postings in sorted(
            ix.postings.items(),
            key=lambda item: sum(p.tf for p in item[1]),
            reverse=True,
        )[:50]:
            table.add_row(term, str(sum(p.tf for p in postings)))
        console.print(table)
    except (OSError, ValueError, EOFError, pickle.UnpicklingError) as exc:
        logger.error("%s", exc)
        raise typer.Exit(1) from None
