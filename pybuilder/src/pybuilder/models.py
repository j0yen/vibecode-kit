"""Centralized model assignments for all pybuilder pipeline stages.

Colleagues with lower API rate limits benefit from Haiku on mechanical
stages and Sonnet on the build loop — only the independent reviewer needs
Opus. All three can be overridden via environment variables.
"""

from __future__ import annotations

import os

# Mechanical stages: scaffold generation, BAD_PYTHON audit guidance,
# gate receipt reading, stability classification, postmortem summary.
# Fast, cheap, no judgment required.
FAST_MODEL: str = os.environ.get("PYBUILDER_FAST_MODEL", "claude-haiku-4-5-20251001")

# Build loop: PRD intake (5-Whys), iterate-and-prove code generation,
# eval dimension assessment. Requires real reasoning and coding ability.
BUILD_MODEL: str = os.environ.get("PYBUILDER_BUILD_MODEL", "claude-sonnet-4-6")

# Independent reviewer (Stage 4 reviewer receipt). Always the strongest
# available model — this is the adversarial second opinion that prevents
# self-approval. Never downgrade this below Opus without explicit intent.
REVIEW_MODEL: str = os.environ.get("PYBUILDER_REVIEW_MODEL", "claude-opus-4-8")
