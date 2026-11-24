"""Build a real corpus from the installed Python standard library docstrings."""
import ast
import sysconfig
from pathlib import Path


def main():
    root = Path(sysconfig.get_path("stdlib"))
    target = Path("data/python_docs")
    target.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in root.rglob("*.py"):
        relative = path.relative_to(root)
        if any(part in {"site-packages", "__pycache__"} for part in relative.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, SyntaxError):
            continue
        for i, node in enumerate(ast.walk(tree)):
            if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            doc = ast.get_docstring(node)
            if not doc:
                continue
            output = target / relative.parent / f"{path.stem}-{i}.txt"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(doc, encoding="utf-8")
            count += 1
    print(f"Extracted {count} documentation passages")


if __name__ == "__main__":
    main()
