"""Unicode-aware streaming tokenizer."""

import re
import unicodedata
from collections.abc import Iterator

WORDS = re.compile(r"[^\W_]+(?:'[^\W_]+)*")


def tokenize(text: str) -> Iterator[str]:
    clean = unicodedata.normalize("NFC", text).casefold()
    clean = clean.replace("’", "'").replace("ʼ", "'")
    for match in WORDS.finditer(clean):
        yield match.group()
