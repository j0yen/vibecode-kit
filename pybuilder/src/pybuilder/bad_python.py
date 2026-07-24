"""BAD_PYTHON audit — AST-based anti-pattern scan.

The Python analog of autobuilder's ``bad-rust.md`` + ``audit-checks.sh``: catch the
semantic footguns ruff doesn't, using the ``ast`` module (no execution of untrusted
code). Findings are ``blocking`` or ``advisory``; the gate blocks on any blocking
finding. The curated set grows via the Stage-5 evolve loop (vision OQ-3 fixes the
initial advisory/blocking split).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Severity(StrEnum):
    BLOCKING = "blocking"
    ADVISORY = "advisory"


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: Severity
    file: str
    line: int
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "rule": self.rule,
            "severity": self.severity.value,
            "file": self.file,
            "line": self.line,
            "message": self.message,
        }


class _Visitor(ast.NodeVisitor):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.findings: list[Finding] = []

    def _add(self, rule: str, sev: Severity, node: ast.AST, msg: str) -> None:
        self.findings.append(
            Finding(rule, sev, self.filename, getattr(node, "lineno", 0), msg)
        )

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        # bare `except:` or `except Exception:` that only passes (swallowed error)
        if node.type is None:
            self._add("bare-except", Severity.BLOCKING, node, "bare `except:` catches everything")
        body_is_pass = len(node.body) == 1 and isinstance(node.body[0], ast.Pass)
        if body_is_pass:
            self._add(
                "swallowed-exception",
                Severity.BLOCKING,
                node,
                "exception body is a bare `pass` — error is silently swallowed",
            )
        self.generic_visit(node)

    def _check_mutable_defaults(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for default in node.args.defaults + node.args.kw_defaults:
            if isinstance(default, ast.List | ast.Dict | ast.Set | ast.ListComp):
                self._add(
                    "mutable-default-arg",
                    Severity.BLOCKING,
                    default,
                    "mutable default argument is shared across calls",
                )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_mutable_defaults(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_mutable_defaults(node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
            self._add(
                f"{node.func.id}-call",
                Severity.BLOCKING,
                node,
                f"`{node.func.id}()` executes dynamic code — refuse on untrusted input",
            )
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        # asserts are stripped under `python -O`; advisory, not blocking.
        self._add(
            "assert-in-source",
            Severity.ADVISORY,
            node,
            "`assert` in non-test source is a no-op under -O; raise explicitly",
        )
        self.generic_visit(node)


def audit_source(source: str, filename: str = "<string>") -> list[Finding]:
    """Audit a source string. A syntax error is itself a blocking finding."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        return [Finding("syntax-error", Severity.BLOCKING, filename, exc.lineno or 0, str(exc))]
    visitor = _Visitor(filename)
    visitor.visit(tree)
    return visitor.findings


def audit_path(path: str | Path) -> list[Finding]:
    """Audit a file or recursively audit a directory's ``*.py`` files."""
    p = Path(path)
    files = sorted(p.rglob("*.py")) if p.is_dir() else [p]
    findings: list[Finding] = []
    for f in files:
        findings.extend(audit_source(f.read_text(encoding="utf-8"), str(f)))
    return findings


def blocking(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity is Severity.BLOCKING]
