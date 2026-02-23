# Public Skills Metadata (Sanitized Example)

This folder demonstrates the **skills metadata pattern** used in the larger private
system without exposing the full runtime router/policy implementation.

## What This Shows

- A central `registry.yaml` as the runtime-oriented source of truth.
- Per-skill folders with human-readable `SKILL.md`.
- Per-skill `toolset.yaml` to show declared tool usage at the skill level.

## What This Does Not Show

- The private routing policy (selection heuristics, budgeting, escalation).
- Full drift-guard CI and sync scripts from the private repo.
- Decision/memory guardrail internals.

## Why Include This In The Public Slice

Recruiters and reviewers can see how the agent framework is organized beyond a
single monolithic "call tools and prompt LLM" file:

1. Skills are declarative.
2. Tools are named and constrained.
3. Behavior can be composed from metadata + code.

In this public slice, the verification runtime remains intentionally simple and
continues to call the demo tools directly.
