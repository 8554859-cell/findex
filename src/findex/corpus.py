"""Read one text document at a time."""

import json
import logging
from typing import cast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Document:
    doc_id: str
    path: Path
    text: str


def iter_documents(root: Path) -> Iterator[Document]:
    if root.is_file() and root.suffix == ".jsonl":
        with root.open(encoding="utf-8") as stream:
            for line in stream:
                row = cast(dict[str, str], json.loads(line))
                yield Document(row["url"], root, row["text"])
        return
    for path in root.rglob("*.txt"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeError, OSError) as exc:
            logger.warning("Skipping %s: %s", path, exc)
            continue
        yield Document(path.relative_to(root).as_posix(), path, text)
