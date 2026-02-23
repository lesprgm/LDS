# Public Portfolio Slice: AI-Assisted Settlement Discovery Engine

This folder is a **sanitized public subset** of a larger production-grade system.
It is intended for recruiter and portfolio review, while keeping core product IP,
source integrations, and operations tooling private.

## What This Public Slice Demonstrates

- Typed LLM extraction into structured settlement schemas (`extraction/`).
- Deterministic-first, multi-signal verification agent with bounded web/tool fan-out + final verdict (`verification/`).
- Concurrency helpers for controlled async execution (`framework/`).
- Simplified evidence-pack generation pipeline (client/internal HTML variants) (`evidence/`).
- Model-agnostic LLM client wiring (OpenRouter/OpenAI/Anthropic) with strict JSON output parsing (`llm/`).

## Why This Code Is Simplified

The full proprietary architecture includes source-specific scrapers, private ranking
logic, business data pipelines, and production telemetry not included here.
This repo preserves the technical patterns and decision flow without exposing
confidential implementation details.

## Architecture (Public Slice)

This repo follows a layered architecture: deterministic orchestration around
LLM-assisted reasoning. The LLM is used for extraction and final synthesis,
while tool fan-out, error handling, and artifact rendering remain explicit code.

| Layer | Purpose | Key Files |
|---|---|---|
| Config | Provider/model wiring through environment variables | `config/settings.py` |
| LLM Interface | Standardized model client + strict JSON parsing helpers (LangChain provider clients used as thin adapters) | `llm/client_factory.py`, `llm/structured_json.py` |
| Extraction | Convert unstructured settlement text into typed rules | `extraction/schemas.py`, `extraction/settlement_extractor.py` |
| Verification | Gather multi-source signals, then issue one eligibility verdict | `verification/tools.py`, `verification/agent.py`, `verification/schemas.py` |
| Concurrency Runtime | Controlled async fan-out/fan-in primitives | `framework/fanout.py` |
| Skills Metadata (Demo) | Declarative skill/tool organization pattern used by the private agent runtime (sanitized examples) | `skills/registry.yaml`, `skills/*/SKILL.md`, `skills/*/toolset.yaml` |
| Evidence Output | Render client/internal HTML evidence packs | `evidence/generator.py`, `evidence/demo.py` |

## End-to-End Flow

1. A settlement document is normalized to plain text and mapped into `SettlementRules`.
2. A candidate business and settlement are passed to the verification agent.
3. Five research tools run concurrently (website, Wayback archive continuity, platform, general context, reviews).
   - Wayback check uses `web.archive.org/cdx/search/cdx` and treats earliest matching business-identity capture as stronger than oldest domain capture.
   - General/review search uses the provided business location fields (no Ohio-only hardcoding).
4. Tool findings are consolidated into one reasoning prompt.
5. The LLM returns a typed `VerificationResult` through schema-validated JSON parsing.
6. Evidence-pack generation produces two artifacts:
   - Client report with plain-language eligibility context.
   - Internal report with confidence, checks performed, and tool findings.

## Runtime Sequence (Verification Path)

```mermaid
flowchart LR
    A[Business + Settlement Input] --> B[verification.agent.verify_candidate]
    B --> C[Parallel Tools in verification.tools]
    C --> D[Findings Consolidation]
    D --> E[llm.structured_json.ainvoke_pydantic]
    E --> F[VerificationResult]
    F --> G[evidence.generator.generate_dual_packs]
    G --> H[CLIENT.html + INTERNAL.html]
```

## Design Choices Visible in This Repo

- Typed boundaries: extraction and verification outputs are Pydantic models.
- Fail-soft behavior: tool failures are captured as findings instead of crashing flow.
- Explicit concurrency limits: async fan-out uses bounded helpers, not unbounded gather.
- Temporal identity safeguards: archive checks account for possible domain reuse/owner changes.
- Model portability: provider switch lives in config, not business logic.
- Agent organization pattern is visible via a sanitized skills registry + per-skill metadata.
- Separation of concerns: search/tooling, LLM reasoning, and rendering are decoupled.
- Dual-audience output: same core signals feed both client-safe and internal artifacts.

## What Is Intentionally Omitted

- Proprietary data connectors and source-specific scraping internals.
- Production ranking, lead-routing, and commercial scoring calibration.
- Full telemetry, cost instrumentation, and deployment/ops infrastructure.

## Quickstart

```bash
cd public-portfolio
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

If you use OpenRouter and do not have a public website yet, leave
`OPENROUTER_HTTP_REFERER` blank in `.env`. The client only sends those headers
when you explicitly set them.

Run tests:

```bash
pytest -q
```

## Runnable Demo Command

Generate sanitized sample evidence packs (no API keys or live scraping required):

```bash
python3 -m evidence.demo --out output/evidence_demo
```

Expected outputs:

- `output/evidence_demo/Acme_Bakery_CLIENT.html`
- `output/evidence_demo/Acme_Bakery_INTERNAL.html`

## Project Layout

- `config/` settings for model/provider wiring.
- `llm/` client factory + structured JSON helpers.
- `extraction/` schema + extraction orchestration.
- `verification/` verification tools, schemas, and agent orchestration.
- `framework/` shared fan-out/concurrency helpers.
- `skills/` sanitized metadata examples showing how the private runtime organizes skills and tool bindings.
- `evidence/` simplified evidence-pack renderer and demo runner.
- `tests/` unit tests for extraction, verification, and evidence generation.

## Skills Metadata Example (Public)

The `skills/` folder is included to show the **declarative skill registry pattern**
used in the larger system:

- `skills/registry.yaml` acts as the source of truth for skill and tool metadata.
- Each skill has a folder with `SKILL.md` (human-readable purpose/safety notes).
- `toolset.yaml` shows the tool bindings the skill is allowed to use.

This public slice does **not** include the full production router/policy runtime for
executing these skills; that logic remains private. The goal is to expose the
architecture pattern, not the proprietary orchestration behavior.

## Notes for Reviewers

- This code is intentionally scoped to show architecture and quality practices.
- Production data, private integrations, and operational workflows are excluded.
