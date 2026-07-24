"""BAD_PYTHON AST audit."""

from __future__ import annotations

from pybuilder.bad_python import audit_source, blocking


def test_bare_except_blocks() -> None:
    src = "try:\n    x = 1\nexcept:\n    pass\n"
    findings = audit_source(src)
    rules = {f.rule for f in findings}
    assert "bare-except" in rules
    assert "swallowed-exception" in rules
    assert blocking(findings)


def test_mutable_default_arg_blocks() -> None:
    src = "def f(x=[]):\n    return x\n"
    findings = audit_source(src)
    assert any(f.rule == "mutable-default-arg" for f in findings)
    assert blocking(findings)


def test_eval_call_blocks() -> None:
    findings = audit_source("eval(user_input)\n")
    assert any(f.rule == "eval-call" for f in findings)
    assert blocking(findings)


def test_clean_code_has_no_blocking_findings() -> None:
    src = (
        "def add(a: int, b: int) -> int:\n"
        "    try:\n"
        "        return a + b\n"
        "    except TypeError as exc:\n"
        "        raise ValueError('bad') from exc\n"
    )
    assert not blocking(audit_source(src))


def test_assert_is_advisory_not_blocking() -> None:
    findings = audit_source("assert x > 0\n")
    assert findings
    assert not blocking(findings)


def test_syntax_error_is_blocking() -> None:
    findings = audit_source("def (:\n")
    assert any(f.rule == "syntax-error" for f in findings)
    assert blocking(findings)
