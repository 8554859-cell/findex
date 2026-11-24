"""Recursive descent Boolean and positional query language."""
import re
from dataclasses import dataclass

from findex.tokenize import tokenize


class Node:
    def __and__(self, other):
        return And(self, other)

    def __or__(self, other):
        return Or(self, other)

    def __invert__(self):
        return Not(self)


@dataclass(frozen=True)
class Term(Node):
    value: str

    def evaluate(self, index):
        return {p.doc_id for p in index.postings.get(self.value, ())}


@dataclass(frozen=True)
class Phrase(Node):
    words: tuple

    def evaluate(self, index):
        if not self.words:
            return set()
        maps = [{p.doc_id: set(p.positions) for p in index.postings.get(w, ())}
                for w in self.words]
        candidates = set.intersection(*(set(m) for m in maps))
        return {d for d in candidates if any(
            all(pos+i in m[d] for i, m in enumerate(maps))
            for pos in maps[0][d])}


@dataclass(frozen=True)
class And(Node):
    left: Node
    right: Node

    def evaluate(self, index):
        return self.left.evaluate(index) & self.right.evaluate(index)


@dataclass(frozen=True)
class Or(Node):
    left: Node
    right: Node

    def evaluate(self, index):
        return self.left.evaluate(index) | self.right.evaluate(index)


@dataclass(frozen=True)
class Not(Node):
    child: Node

    def evaluate(self, index):
        return set(index.doc_meta) - self.child.evaluate(index)


def parse(query):
    tokens = re.findall(r'"[^"]*"|[()]|[^\s()"]+', query)
    if query.count('"') % 2:
        raise ValueError("Unclosed quote")
    cursor = 0

    def peek():
        return tokens[cursor] if cursor < len(tokens) else None

    def take():
        nonlocal cursor
        value = peek()
        if value is None:
            raise ValueError("Missing operand")
        cursor += 1
        return value

    def unary():
        token = take()
        if token == "NOT":
            return ~unary()
        if token == "(":
            node = disjunction()
            if take() != ")":
                raise ValueError("Expected closing parenthesis")
            return node
        if token in {"AND", "OR", ")"}:
            raise ValueError("Unexpected operator")
        words = tuple(tokenize(token))
        if not words:
            raise ValueError("Empty term")
        if token.startswith('"'):
            return Phrase(words)
        node = Term(words[0])
        for word in words[1:]:
            node &= Term(word)
        return node

    def conjunction():
        node = unary()
        while peek() not in (None, "OR", ")"):
            if peek() == "AND":
                take()
            node &= unary()
        return node

    def disjunction():
        node = conjunction()
        while peek() == "OR":
            take()
            node |= conjunction()
        return node

    result = disjunction()
    if peek() is not None:
        raise ValueError("Unexpected trailing token")
    return result


def positive_terms(node):
    if isinstance(node, Term):
        return {node.value}
    if isinstance(node, Phrase):
        return set(node.words)
    if isinstance(node, Not):
        return set()
    return positive_terms(node.left) | positive_terms(node.right)
