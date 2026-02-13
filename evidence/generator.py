"""Simple HTML evidence-pack generation for a public, sanitized portfolio."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any, Mapping, Sequence


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()  # Pydantic v2
    if hasattr(value, "dict"):
        return value.dict()  # Pydantic v1
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _slugify(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value.strip())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    cleaned = cleaned.strip("_")
    return cleaned or "evidence_pack"


def _render_list(items: Sequence[str], empty_text: str) -> str:
    normalized = [str(item).strip() for item in items if str(item).strip()]
    if not normalized:
        return f"<p>{escape(empty_text)}</p>"
    bullets = "\n".join(f"<li>{escape(item)}</li>" for item in normalized)
    return f"<ul>{bullets}</ul>"


def _render_evidence_rows(evidence: Sequence[dict[str, Any]]) -> str:
    if not evidence:
        return "<p>No tool findings captured.</p>"

    parts = ["<ul>"]
    for finding in evidence:
        source = escape(str(finding.get("source", "unknown")))
        detail = escape(str(finding.get("finding", "")))
        support = finding.get("supports_eligibility")
        support_text = "supports" if support is True else "contradicts" if support is False else "neutral"
        url = finding.get("url")
        url_text = f" (<a href=\"{escape(str(url))}\">{escape(str(url))}</a>)" if url else ""
        parts.append(f"<li><strong>{source}</strong> [{support_text}] {detail}{url_text}</li>")
    parts.append("</ul>")
    return "\n".join(parts)


def build_pack_html(
    business: Mapping[str, Any],
    settlement: Any,
    verification: Any,
    *,
    pack_type: str = "client",
    screenshot_paths: Sequence[str] | None = None,
    generated_at: str | None = None,
) -> str:
    """Build a single HTML evidence pack.

    `pack_type` controls content detail:
    - `client`: clear outcome + next steps.
    - `internal`: includes additional verification diagnostics.
    """
    if pack_type not in {"client", "internal"}:
        raise ValueError("pack_type must be 'client' or 'internal'")

    settlement_data = _as_dict(settlement)
    verification_data = _as_dict(verification)
    screenshot_paths = screenshot_paths or []
    generated_at = generated_at or datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    business_name = str(business.get("name", "Unknown Business"))
    city = str(business.get("city", ""))
    category = str(business.get("category", ""))
    website = str(business.get("website", ""))

    settlement_name = str(settlement_data.get("settlement_name", "Unknown Settlement"))
    summary = str(settlement_data.get("summary", "")).strip() or "Summary not available in this public demo."
    deadline = str(settlement_data.get("claim_deadline") or "Not provided")
    claim_url = str(settlement_data.get("claim_url") or "")
    claim_method = str(settlement_data.get("claim_method") or "online")
    class_desc = str(settlement_data.get("eligible_class_description") or "Not provided")
    actions = settlement_data.get("eligible_actions") or []
    proof_required = settlement_data.get("proof_required") or []

    verdict = str(verification_data.get("verdict", "unknown")).upper()
    confidence = int(verification_data.get("confidence", 0))
    reasoning = str(verification_data.get("reasoning", "")).strip()
    checks = verification_data.get("checks_performed") or []
    evidence = verification_data.get("evidence") or []

    claim_link_html = (
        f"<a href=\"{escape(claim_url)}\">{escape(claim_url)}</a>" if claim_url else "Not available in this demo"
    )
    website_html = f"<a href=\"{escape(website)}\">{escape(website)}</a>" if website else "Not provided"

    actions_html = _render_list(actions, "No specific qualifying actions were extracted.")
    proof_html = _render_list(proof_required, "No specific proof requirements were extracted.")
    screenshots_html = _render_list(screenshot_paths, "No screenshot references included in this sample.")

    internal_section = ""
    if pack_type == "internal":
        checks_html = _render_list(checks, "No check metadata captured.")
        evidence_html = _render_evidence_rows(evidence)
        internal_section = f"""
        <section>
          <h2>Internal QA Signals</h2>
          <p><strong>Confidence:</strong> {confidence}</p>
          <p><strong>Reasoning:</strong> {escape(reasoning or "Not provided")}</p>
          <h3>Checks Performed</h3>
          {checks_html}
          <h3>Tool Findings</h3>
          {evidence_html}
        </section>
        """

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(business_name)} - {escape(settlement_name)} ({pack_type.title()})</title>
  <style>
    :root {{
      --bg: #f7f7f2;
      --card: #ffffff;
      --ink: #1f2a30;
      --accent: #0f766e;
      --muted: #637177;
      --border: #dfe5e7;
    }}
    body {{
      margin: 0;
      padding: 2rem 1rem;
      background: radial-gradient(circle at top right, #e8f5f3, var(--bg));
      color: var(--ink);
      font: 16px/1.5 "Georgia", "Times New Roman", serif;
    }}
    main {{
      max-width: 900px;
      margin: 0 auto;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1.5rem;
      box-shadow: 0 8px 30px rgba(20, 40, 50, 0.08);
    }}
    h1, h2, h3 {{ line-height: 1.2; }}
    h1 {{ margin-top: 0; }}
    .meta {{
      color: var(--muted);
      margin-bottom: 1rem;
      font-size: 0.95rem;
    }}
    .badge {{
      display: inline-block;
      background: #e6f4f1;
      border: 1px solid #bfe3dc;
      color: #0b5e57;
      border-radius: 999px;
      padding: 0.2rem 0.6rem;
      font-size: 0.85rem;
      margin-right: 0.4rem;
    }}
    section {{
      margin-top: 1.25rem;
      padding-top: 1rem;
      border-top: 1px solid var(--border);
    }}
    code {{
      font-family: "SFMono-Regular", Menlo, Consolas, "Liberation Mono", monospace;
      background: #f2f5f7;
      border-radius: 5px;
      padding: 0.08rem 0.3rem;
    }}
    a {{ color: var(--accent); }}
  </style>
</head>
<body>
  <main>
    <h1>Settlement Evidence Pack ({pack_type.title()})</h1>
    <p class="meta">
      Generated: {escape(generated_at)}<br>
      Public portfolio artifact. Sanitized to demonstrate workflow patterns from a larger proprietary system.
    </p>

    <p>
      <span class="badge">Business: {escape(business_name)}</span>
      <span class="badge">Settlement: {escape(settlement_name)}</span>
      <span class="badge">Verdict: {escape(verdict)}</span>
    </p>

    <section>
      <h2>Business Snapshot</h2>
      <p><strong>Location:</strong> {escape(city or "Unknown city")}</p>
      <p><strong>Category:</strong> {escape(category or "Unknown category")}</p>
      <p><strong>Website:</strong> {website_html}</p>
    </section>

    <section>
      <h2>Eligibility Snapshot</h2>
      <p>{escape(summary)}</p>
      <p><strong>Class description:</strong> {escape(class_desc)}</p>
      <p><strong>Claim deadline:</strong> {escape(deadline)}</p>
      <p><strong>Claim method:</strong> {escape(claim_method)}</p>
      <p><strong>Claim link:</strong> {claim_link_html}</p>
      <h3>Qualifying Signals</h3>
      {actions_html}
    </section>

    <section>
      <h2>Potential Supporting Documents</h2>
      {proof_html}
    </section>

    <section>
      <h2>Asset References</h2>
      {screenshots_html}
    </section>

    {internal_section}
  </main>
</body>
</html>
"""


def write_evidence_pack(
    business: Mapping[str, Any],
    settlement: Any,
    verification: Any,
    *,
    out_dir: str | Path,
    pack_type: str = "client",
    screenshot_paths: Sequence[str] | None = None,
    generated_at: str | None = None,
) -> Path:
    """Render and write one evidence pack to disk."""
    business_name = str(business.get("name", "Unknown Business"))
    slug = _slugify(business_name)
    suffix = "CLIENT" if pack_type == "client" else "INTERNAL"
    out_path = Path(out_dir) / f"{slug}_{suffix}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    html = build_pack_html(
        business,
        settlement,
        verification,
        pack_type=pack_type,
        screenshot_paths=screenshot_paths,
        generated_at=generated_at,
    )
    out_path.write_text(html, encoding="utf-8")
    return out_path


def generate_dual_packs(
    business: Mapping[str, Any],
    settlement: Any,
    verification: Any,
    *,
    out_dir: str | Path,
    screenshot_paths: Sequence[str] | None = None,
    generated_at: str | None = None,
) -> dict[str, Path]:
    """Write both client and internal pack variants for one candidate."""
    return {
        "client": write_evidence_pack(
            business,
            settlement,
            verification,
            out_dir=out_dir,
            pack_type="client",
            screenshot_paths=screenshot_paths,
            generated_at=generated_at,
        ),
        "internal": write_evidence_pack(
            business,
            settlement,
            verification,
            out_dir=out_dir,
            pack_type="internal",
            screenshot_paths=screenshot_paths,
            generated_at=generated_at,
        ),
    }
