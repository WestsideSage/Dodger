---
name: dodgeball-systems-balance
description: Use when Dodgeball Manager work asks for systems balance, decision quality, tactic/lineup/recruiting/development impact, simulation health, parity, tuning, probes, or evidence-backed gameplay refinement.
---

# Dodgeball Systems Balance

Use this skill for high-effort systems design, balance, and simulation-health work in Dodgeball Manager.

## Operating Stance

Answer the core question: does the actual decision space produce interesting, understandable, repeatable, manager-driven outcomes across seasons?

Stay evidence-bound. If evidence is missing, say so and mark the claim unverified. Do not infer current behavior from stale plans or docs.

If the user requests read-only, review-only, or browser-only work, obey that boundary. Otherwise, safe implementation is allowed only after the problem is proven.

## Orientation

Start from live repo truth:

1. Confirm repo path, branch, and dirty status.
2. Read `AGENTS.md`, `docs/README.md`, `docs/STATUS.md`, and `docs/specs/MILESTONES.md`.
3. Read `CLAUDE.md` and `docs/specs/long-range-playable-roadmap.md` when making broad systems claims.
4. Inspect relevant engine/domain files before making claims: `engine.py`, `official_engine.py`, `official_resolution.py`, `config.py`, `models.py`, `rng.py`, `season.py`, `playoffs.py`, `development.py`, `recruitment.py`, `scouting.py`, `ai_program_manager.py`, and `use_cases.py`.
5. Inspect relevant tests and probes under `tests/` and `tools/`.

Use Pare MCP commands where available and useful. If Pare is unavailable, unsuitable, or raw output is needed, use normal shell/git commands and state that fallback in the handoff.

## Non-Negotiables

- No hidden user boosts, rubber-banding, comeback code, unseeded randomness, or animation-driven outcomes.
- Preserve deterministic RNG through `DeterministicRNG` and `derive_seed`.
- Do not change outcomes casually. Outcome-affecting changes need before/after measurement, tests, and a design reason.
- Do not hardcode balance constants in engine logic when config is the right layer.
- Do not invent unresolved official-rules behavior.
- Do not make UI changes except to expose system truth or verify gameplay.
- If a reported issue is already fixed, report the evidence and do not force a diff.

## Workflow

1. Build a systems map.
   Inventory weekly intent, orders, lineup, tactics, scout opponent, recruiting, scouting prospects, development, staff, AI managers, playoffs, ceremonies, records, awards, replay, and aftermath. For each, identify inputs, outputs, hidden state, visible state, and player decisions.

2. Audit causality.
   For each decision, trace where it enters code, whether it affects outcome, presentation, both, or neither, and whether the player can see enough evidence to understand it.

3. Run targeted probes.
   Use existing tests/tools first. Measure favorite win rates, draw rates, score distributions, match length, upset rates, tactic impact, lineup impact, development distribution, recruiting outcomes, AI parity, and multi-season league health where relevant.

4. Classify findings.
   Use these labels: bug, balance issue, legibility issue, design gap, instrumentation gap, or owner decision.

5. Implement safe improvements.
   Prefer clear bug fixes, tests, probes, and small config-backed tuning with evidence. For larger redesigns, write a focused plan instead of half-shipping.

6. Verify.
   Run focused tests for touched systems. Run full `python -m pytest -q` for broad domain/outcome changes. Run probes before/after. Run frontend build/lint only if presentation code changes.

## Required Analysis

Explicitly answer:

- Top 5 highest-leverage systems issues.
- Player decisions that currently matter most.
- Decisions that appear to matter but may not matter enough.
- Systems at risk of solved or degenerate play.
- Systems too opaque for new-player trust.
- Outcomes likely to feel unfair even if technically correct.
- Balance numbers that should become ongoing gates.
- Areas that should not be touched yet because evidence is insufficient.

## Handoff

Provide: systems verdict, evidence inspected, measurements, implemented changes by system, exact tests/checks run, open owner decisions, and ranked next systems pass.
