"""pybuilder command-line entrypoint.

Subcommands map to pipeline stages:

    pybuilder scaffold <intent-card.json> <dest>   # generate a locked-harness project
    pybuilder audit    <path>                        # BAD_PYTHON anti-pattern scan
    pybuilder gate     <project> --target <t>        # receipt-based ready/blocked
    pybuilder demo                                   # run the worked example end-to-end

Intake (PRD → intent card) is an LLM step driven by the skill prompt, not this CLI;
``scaffold`` takes the resulting ``intent-card.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .bad_python import Severity, audit_path, blocking
from .gate import evaluate_gate
from .intent_card import IntentCard, IntentCardError
from .receipts import ReceiptStore
from .scaffold import ScaffoldError, scaffold


def _cmd_scaffold(args: argparse.Namespace) -> int:
    try:
        card = IntentCard.load(args.intent_card)
    except (OSError, json.JSONDecodeError, IntentCardError) as exc:
        print(f"intake error: {exc}", file=sys.stderr)
        return 2
    try:
        root = scaffold(card, args.dest, force=args.force)
    except ScaffoldError as exc:
        print(f"scaffold error: {exc}", file=sys.stderr)
        return 2
    print(f"scaffolded {card.target} project {card.slug} -> {root}")
    return 0


def _cmd_audit(args: argparse.Namespace) -> int:
    findings = audit_path(args.path)
    for f in findings:
        marker = "BLOCK" if f.severity is Severity.BLOCKING else "warn "
        print(f"{marker} {f.file}:{f.line} [{f.rule}] {f.message}")
    blockers = blocking(findings)
    print(f"\n{len(findings)} finding(s), {len(blockers)} blocking")
    return 1 if blockers else 0


def _cmd_gate(args: argparse.Namespace) -> int:
    store = ReceiptStore(args.project)
    verdict = evaluate_gate(store, args.target)
    print(json.dumps(verdict.to_dict(), indent=2))
    return 0 if verdict.ready else 1


def _cmd_demo(_args: argparse.Namespace) -> int:
    from .examples_demo import run_demo

    run_demo()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pybuilder", description="PRD-driven Python code generation.")
    p.add_argument("--version", action="version", version=f"pybuilder {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("scaffold", help="generate a locked-harness project from an intent card")
    sp.add_argument("intent_card", type=Path)
    sp.add_argument("dest", type=Path)
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(func=_cmd_scaffold)

    ap = sub.add_parser("audit", help="BAD_PYTHON anti-pattern scan")
    ap.add_argument("path", type=Path)
    ap.set_defaults(func=_cmd_audit)

    gp = sub.add_parser("gate", help="receipt-based ready/blocked verdict")
    gp.add_argument("project", type=Path)
    gp.add_argument("--target", choices=["cli", "lib", "agent"], default="lib")
    gp.set_defaults(func=_cmd_gate)

    dp = sub.add_parser("demo", help="run the worked example end-to-end")
    dp.set_defaults(func=_cmd_demo)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
