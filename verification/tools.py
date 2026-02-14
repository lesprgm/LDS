import asyncio
import logging
import re
from datetime import datetime
from urllib.parse import urlparse

import httpx

from verification.schemas import SubAgentFinding

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
_ALT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
_TIMEOUT = httpx.Timeout(12.0, connect=8.0)
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_WAYBACK_TIMEOUT = httpx.Timeout(20.0, connect=8.0)
_WAYBACK_CDX_URL = "https://web.archive.org/cdx/search/cdx"
_WAYBACK_VIEW_BASE = "https://web.archive.org/web"
_OWNER_CHANGE_MARKERS = (
    "under new ownership",
    "new ownership",
    "formerly",
    "now known as",
    "rebranded",
    "acquired",
)
_TOKEN_STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "your", "you", "our",
    "llc", "inc", "co", "company", "ltd", "group", "services", "service",
}


def _extract_text(html: str, max_chars: int = 4000) -> str:
    """Strip HTML tags and collapse whitespace."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _domain_from_website(website_url: str) -> str:
    """Normalize a website URL to a bare host."""
    url = website_url.strip()
    if not url:
        return ""
    if "://" not in url:
        url = f"https://{url}"
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def _wayback_iso_date(timestamp: str) -> str | None:
    """Convert Wayback timestamp YYYYMMDDhhmmss to ISO date."""
    if not timestamp:
        return None
    try:
        return datetime.strptime(timestamp[:14], "%Y%m%d%H%M%S").date().isoformat()
    except ValueError:
        return None


def _sample_wayback_rows(rows: list[list[str]], max_samples: int = 8) -> list[list[str]]:
    """Sample chronological rows while preserving earliest/latest captures."""
    if len(rows) <= max_samples:
        return rows
    idxs = {0, 1, min(2, len(rows) - 1), len(rows) - 1}
    step = max(1, (len(rows) - 1) // (max_samples - 1))
    for i in range(0, len(rows), step):
        idxs.add(i)
        if len(idxs) >= max_samples:
            break
    return [rows[i] for i in sorted(idxs) if 0 <= i < len(rows)]


def _identity_score(page_text: str, business_name: str, city: str) -> tuple[float, bool]:
    """Score whether a historical snapshot appears to be the same business identity."""
    text = (page_text or "").lower()
    cleaned_name = re.sub(r"[^a-z0-9 ]+", " ", (business_name or "").lower())
    cleaned_name = re.sub(r"\s+", " ", cleaned_name).strip()
    if not cleaned_name:
        return 0.0, False

    tokens = [t for t in cleaned_name.split() if len(t) >= 4 and t not in _TOKEN_STOPWORDS]
    phrase_hit = cleaned_name in text
    token_hits = sum(1 for t in tokens if re.search(rf"\b{re.escape(t)}\b", text))
    token_ratio = token_hits / max(1, len(tokens))
    city_hit = bool(city and re.search(rf"\b{re.escape(city.lower())}\b", text))

    score = 0.0
    score += 0.7 if phrase_hit else 0.6 * token_ratio
    if city_hit:
        score += 0.2
    if token_hits >= 2:
        score += 0.1
    score = min(score, 1.0)

    owner_change_signal = any(marker in text for marker in _OWNER_CHANGE_MARKERS)
    return score, owner_change_signal


async def _ddg_search_with_retry(query: str, max_results: int = 5, attempts: int = 2) -> list[dict]:
    """Run a DuckDuckGo text search with retry on failure."""
    from duckduckgo_search import DDGS

    ddg = DDGS()
    last_err = None
    for attempt in range(attempts):
        try:
            return ddg.text(query, max_results=max_results)
        except Exception as e:
            last_err = e
            logger.debug(f"DDG search attempt {attempt+1} failed for '{query}': {e}")
            if attempt < attempts - 1:
                await asyncio.sleep(2)
    logger.warning(f"DDG search exhausted retries for '{query}': {last_err}")
    return []


async def check_business_website(website_url: str, settlement_context: dict) -> SubAgentFinding:
    """Fetch the business website and extract text for LLM analysis."""
    if not website_url:
        return SubAgentFinding(
            source="business_website",
            finding="No website available for this business",
            supports_eligibility=None,
        )

    last_error = None
    for attempt in range(3):
        headers = _HEADERS if attempt < 2 else _ALT_HEADERS
        try:
            async with httpx.AsyncClient(headers=headers, timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(website_url)

                if resp.status_code in _RETRYABLE_STATUS:
                    last_error = f"HTTP {resp.status_code}"
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue

                if resp.status_code == 403 and attempt == 0:
                    last_error = "HTTP 403 Forbidden"
                    await asyncio.sleep(1)
                    continue

                resp.raise_for_status()
                text = _extract_text(resp.text, max_chars=4000)

            if len(text) < 50:
                return SubAgentFinding(
                    source="business_website",
                    url=website_url,
                    finding="Website returned minimal content (possibly JS-rendered or down)",
                    supports_eligibility=None,
                )

            return SubAgentFinding(
                source="business_website",
                url=website_url,
                finding=f"Website content: {text[:3500]}",
                supports_eligibility=None,
            )

        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            last_error = f"{type(e).__name__}: {e}"
            await asyncio.sleep(1.5 * (attempt + 1))
            continue
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            break

    return SubAgentFinding(
        source="business_website",
        url=website_url,
        finding="Business website was unreachable at time of verification",
        supports_eligibility=None,
        is_error=True,
        error_detail=f"Failed to fetch website: {last_error}",
    )


async def search_platform_presence(business_name: str, city: str, settlement_context: dict) -> SubAgentFinding:
    """Search for the business on settlement-relevant platforms (via DDG)."""
    defendant = settlement_context.get("defendant", "")
    settlement_name = settlement_context.get("settlement_name", "")

    queries: list[str] = []
    if any(kw in settlement_name.lower() or kw in defendant.lower() for kw in ["grubhub", "seamless"]):
        queries.append(f'"{business_name}" {city} grubhub')
        queries.append(f'"{business_name}" {city} site:grubhub.com')
    elif any(kw in settlement_name.lower() or kw in defendant.lower() for kw in ["doordash", "caviar"]):
        queries.append(f'"{business_name}" {city} doordash')
    elif "discover" in settlement_name.lower() or "discover" in defendant.lower():
        queries.append(f'"{business_name}" {city} "accepts discover"')
        queries.append(f'"{business_name}" {city} discover card')
    elif "payment card" in settlement_name.lower() or "interchange" in settlement_name.lower():
        queries.append(f'"{business_name}" {city} credit card payment processing')
    else:
        queries.append(f'"{business_name}" {city} {defendant}')

    results_text: list[str] = []
    try:
        for q in queries[:2]:
            hits = await _ddg_search_with_retry(q, max_results=3)
            for hit in hits:
                results_text.append(f"[{hit.get('title','')}] {hit.get('body','')} ({hit.get('href','')})")
            await asyncio.sleep(1)
    except ImportError:
        return SubAgentFinding(source="platform_search", finding="duckduckgo-search package not available", supports_eligibility=None)

    if not results_text:
        return SubAgentFinding(
            source="platform_search",
            finding=f"No platform presence found for '{business_name}' in {city} related to {defendant}",
            supports_eligibility=None,
        )

    combined = "\n".join(results_text[:6])
    return SubAgentFinding(source="platform_search", finding=f"Platform search results:\n{combined[:2500]}", supports_eligibility=None)


async def search_general_context(business_name: str, city: str, state: str = "OH") -> SubAgentFinding:
    """Search for general info about the business (chain/franchise signals)."""
    try:
        query = f'"{business_name}" {city} {state}'
        hits = await _ddg_search_with_retry(query, max_results=5)
        if not hits:
            return SubAgentFinding(source="general_search", finding=f"No web results found for '{business_name}' in {city}, {state}", supports_eligibility=None)

        results_text = [f"[{h.get('title','')}] {h.get('body','')} ({h.get('href','')})" for h in hits]
        combined = "\n".join(results_text)
        return SubAgentFinding(source="general_search", finding=f"General web search results:\n{combined[:2500]}", supports_eligibility=None)

    except ImportError:
        return SubAgentFinding(
            source="general_search",
            finding="Search package not available",
            supports_eligibility=None,
            is_error=True,
            error_detail="duckduckgo-search package not installed",
        )
    except Exception as e:
        return SubAgentFinding(
            source="general_search",
            finding="General web search was unavailable at time of verification",
            supports_eligibility=None,
            is_error=True,
            error_detail=f"General search failed: {type(e).__name__}: {e}",
        )


async def check_review_presence(business_name: str, city: str, state: str = "OH") -> SubAgentFinding:
    """Search for review/listing presence to confirm business type/history."""
    try:
        query = f'"{business_name}" {city} {state} yelp OR reviews OR "google reviews"'
        hits = await _ddg_search_with_retry(query, max_results=4)
        if not hits:
            return SubAgentFinding(source="review_search", finding=f"No review listings found for '{business_name}' in {city}", supports_eligibility=None)

        results_text = [f"[{h.get('title','')}] {h.get('body','')} ({h.get('href','')})" for h in hits]
        combined = "\n".join(results_text)
        return SubAgentFinding(source="review_search", finding=f"Review/listing search results:\n{combined[:2000]}", supports_eligibility=None)

    except ImportError:
        return SubAgentFinding(
            source="review_search",
            finding="Search package not available",
            supports_eligibility=None,
            is_error=True,
            error_detail="duckduckgo-search package not installed",
        )
    except Exception as e:
        return SubAgentFinding(
            source="review_search",
            finding="Review search was unavailable at time of verification",
            supports_eligibility=None,
            is_error=True,
            error_detail=f"Review search failed: {type(e).__name__}: {e}",
        )


async def check_wayback_history(business_name: str, city: str, website_url: str) -> SubAgentFinding:
    """Check Wayback for earliest matching identity capture (not just earliest domain capture)."""
    if not website_url:
        return SubAgentFinding(
            source="wayback_archive",
            finding="No website available, so archive history could not be evaluated.",
            supports_eligibility=None,
        )

    domain = _domain_from_website(website_url)
    if not domain:
        return SubAgentFinding(
            source="wayback_archive",
            url=website_url,
            finding="Website URL format prevented archive lookup.",
            supports_eligibility=None,
            is_error=True,
            error_detail=f"Invalid website URL: {website_url}",
        )

    params = [
        ("url", f"{domain}/*"),
        ("output", "json"),
        ("fl", "timestamp,original,statuscode,mimetype,digest"),
        ("filter", "statuscode:200"),
        ("filter", "mimetype:text/html"),
        ("collapse", "digest"),
        ("from", "1996"),
        ("limit", "200"),
    ]

    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=_WAYBACK_TIMEOUT, follow_redirects=True) as client:
            cdx_resp = await client.get(_WAYBACK_CDX_URL, params=params)
            cdx_resp.raise_for_status()
            payload = cdx_resp.json()

            if not isinstance(payload, list) or len(payload) <= 1:
                return SubAgentFinding(
                    source="wayback_archive",
                    url=f"{_WAYBACK_VIEW_BASE}/*/{domain}",
                    finding=f"Wayback archive has no HTML captures for {domain} in the sampled index.",
                    supports_eligibility=None,
                )

            rows = [r for r in payload[1:] if isinstance(r, list) and len(r) >= 2]
            rows.sort(key=lambda r: r[0])
            earliest_capture_iso = _wayback_iso_date(rows[0][0]) or "unknown"
            sampled = _sample_wayback_rows(rows)

            sampled_results = []
            for row in sampled:
                ts = row[0]
                original = row[1]
                iso_date = _wayback_iso_date(ts)
                if not iso_date:
                    continue
                snap_url = f"{_WAYBACK_VIEW_BASE}/{ts}id_/{original}"
                try:
                    snap_resp = await client.get(snap_url)
                    if snap_resp.status_code >= 400:
                        continue
                    text = _extract_text(snap_resp.text, max_chars=7000)
                    if len(text) < 40:
                        continue
                except Exception:
                    continue
                score, owner_change = _identity_score(text, business_name, city)
                sampled_results.append(
                    {"date": iso_date, "url": snap_url, "score": score, "owner_change": owner_change, "matched": score >= 0.65}
                )

            if not sampled_results:
                return SubAgentFinding(
                    source="wayback_archive",
                    url=f"{_WAYBACK_VIEW_BASE}/*/{domain}",
                    finding=f"Wayback has captures for {domain} since {earliest_capture_iso}, but sampled snapshots were not parseable.",
                    supports_eligibility=None,
                )

            sampled_results.sort(key=lambda r: r["date"])
            matches = [r for r in sampled_results if r["matched"]]
            if not matches:
                return SubAgentFinding(
                    source="wayback_archive",
                    url=f"{_WAYBACK_VIEW_BASE}/*/{domain}",
                    finding=(
                        f"Wayback captures exist for {domain} since {earliest_capture_iso}, but no sampled snapshot "
                        "confidently matched the current business identity (possible domain reuse/owner change)."
                    ),
                    supports_eligibility=None,
                )

            first_match = matches[0]
            post_match = [r for r in sampled_results if r["date"] >= first_match["date"]]
            continuity = sum(1 for r in post_match if r["matched"]) / len(post_match) if post_match else 0.0
            pre_match_nonmatch = sum(1 for r in sampled_results if r["date"] < first_match["date"] and not r["matched"])
            ownership_flags = sum(1 for r in sampled_results if r["owner_change"])

            caution = ""
            if pre_match_nonmatch > 0:
                caution = " Earlier captures did not match current identity."
            if ownership_flags > 0:
                caution += " Ownership-change wording appears in sampled archives."

            return SubAgentFinding(
                source="wayback_archive",
                url=first_match["url"],
                finding=(
                    f"Wayback domain capture begins {earliest_capture_iso}. "
                    f"Earliest matching business identity capture: {first_match['date']}. "
                    f"Continuity score: {continuity:.2f} across {len(post_match)} sampled snapshots from {domain}.{caution}"
                ),
                supports_eligibility=True if continuity >= 0.6 else None,
            )

    except Exception as e:
        return SubAgentFinding(
            source="wayback_archive",
            url=f"{_WAYBACK_VIEW_BASE}/*/{domain}",
            finding="Wayback archive lookup was unavailable at time of verification.",
            supports_eligibility=None,
            is_error=True,
            error_detail=f"Wayback lookup failed: {type(e).__name__}: {e}",
        )
