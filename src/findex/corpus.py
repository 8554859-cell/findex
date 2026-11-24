"""Read one text document at a time."""
import logging
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterator


@dataclass(frozen=True)
class Document:
    doc_id: str
    path: Path
    text: str


def iter_documents(root: Path) -> Iterator[Document]:
    for path in root.rglob("*.txt"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeError, OSError) as exc:
            logging.warning("Skipping %s: %s", path, exc)
            continue
        yield Document(path.relative_to(root).as_posix(), path, text)
