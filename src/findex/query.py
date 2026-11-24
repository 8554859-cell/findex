"""Recursive descent Boolean and positional query language."""
from __future__ import annotations

import re
from dataclasses import dataclass

from findex.index import Index
from findex.tokenize import tokenize


class Node:
    def evaluate(self, index: Index) -> set[int]:
        raise NotImplementedError

    def __and__(self, other: Node) -> And:
        return And(self, other)

    def __or__(self, other: Node) -> Or:
        return Or(self, other)

    def __invert__(self) -> Not:
        return Not(self)


@dataclass(frozen=True)
class Term(Node):
    value: str

    def evaluate(self, index: Index) -> set[int]:
        return {p.doc_id for p in index.postings.get(self.value, [])}


@dataclass(frozen=True)
class Phrase(Node):
    words: tuple[str, ...]

    def evaluate(self, index: Index) -> set[int]:
        if not self.words:
            return set()
        maps = [{p.doc_id: set(p.positions) for p in index.postings.get(w, [])}
                for w in self.words]
        candidates = set(maps[0]).intersection(*(set(m) for m in maps[1:]))
        return {d for d in candidates if any(
            all(pos+i in m[d] for i, m in enumerate(maps))
            for pos in maps[0][d])}


@dataclass(frozen=True)
class And(Node):
    left: Node
    right: Node

    def evaluate(self, index: Index) -> set[int]:
        return self.left.evaluate(index) & self.right.evaluate(index)


@dataclass(frozen=True)
class Or(Node):
    left: Node
    right: Node

    def evaluate(self, index: Index) -> set[int]:
        return self.left.evaluate(index) | self.right.evaluate(index)


@dataclass(frozen=True)
class Not(Node):
    child: Node

    def evaluate(self, index: Index) -> set[int]:
        return set(index.doc_meta) - self.child.evaluate(index)


def parse(query: str) -> Node:
    tokens = re.findall(r'"[^"]*"|[()]|[^\s()"]+', query)
    if query.count('"') % 2:
        raise ValueError("Unclosed quote")
    cursor = 0

    def peek() -> str | None:
        return tokens[cursor] if cursor < len(tokens) else None

    def take() -> str:
        nonlocal cursor
        value = peek()
        if value is None:
            raise ValueError("Missing operand")
        cursor += 1
        return value

    def unary() -> Node:
        token = take()
        if token == "NOT":
            return ~unary()
        if token == "(":
            group = disjunction()
            if take() != ")":
                raise ValueError("Expected closing parenthesis")
            return group
        if token in {"AND", "OR", ")"}:
            raise ValueError("Unexpected operator")
        words = tuple(tokenize(token))
        if not words:
            raise ValueError("Empty term")
        if token.startswith('"'):
            return Phrase(words)
        node: Node = Term(words[0])
        for word in words[1:]:
            node &= Term(word)
        return node

    def conjunction() -> Node:
        node = unary()
        while peek() not in (None, "OR", ")"):
            if peek() == "AND":
                take()
            node &= unary()
        return node

    def disjunction() -> Node:
        node = conjunction()
        while peek() == "OR":
            take()
            node |= conjunction()
        return node

    result = disjunction()
    if peek() is not None:
        raise ValueError("Unexpected trailing token")
    return result


def positive_terms(node: Node) -> set[str]:
    if isinstance(node, Term):
        return {node.value}
    if isinstance(node, Phrase):
        return set(node.words)
    if isinstance(node, Not):
        return set()
    if isinstance(node, (And, Or)):
        return positive_terms(node.left) | positive_terms(node.right)
    raise TypeError("Unknown query node")
