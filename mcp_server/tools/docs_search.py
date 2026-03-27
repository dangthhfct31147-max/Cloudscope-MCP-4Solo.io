"""Official docs search with local concept fallback for CloudScope."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

try:
    from mcp_server.tools.concept_explainer import find_relevant_concepts
except ImportError:  # pragma: no cover - fallback for direct script execution
    from tools.concept_explainer import find_relevant_concepts


DOC_SOURCES = {
    "kubernetes": {
        "search_url": "https://kubernetes.io/docs/search/?q={query}",
        "base_url": "https://kubernetes.io",
        "allowed_hosts": ["kubernetes.io"],
    },
    "docker": {
        "search_url": "https://docs.docker.com/search/?q={query}",
        "base_url": "https://docs.docker.com",
        "allowed_hosts": ["docs.docker.com"],
    },
    "helm": {
        "search_url": "https://helm.sh/docs/?q={query}",
        "base_url": "https://helm.sh",
        "allowed_hosts": ["helm.sh"],
    },
    "prometheus": {
        "search_url": "https://prometheus.io/search/?q={query}",
        "base_url": "https://prometheus.io",
        "allowed_hosts": ["prometheus.io"],
    },
    "grafana": {
        "search_url": "https://grafana.com/search/?q={query}",
        "base_url": "https://grafana.com",
        "allowed_hosts": ["grafana.com"],
    },
    "istio": {
        "search_url": "https://istio.io/latest/search/?q={query}",
        "base_url": "https://istio.io",
        "allowed_hosts": ["istio.io"],
    },
    "cilium": {
        "search_url": "https://docs.cilium.io/en/stable/search.html?q={query}",
        "base_url": "https://docs.cilium.io",
        "allowed_hosts": ["docs.cilium.io"],
    },
}

TECH_ALIASES = {"k8s": "kubernetes"}
SEARCH_CACHE: dict[str, dict[str, Any]] = {}
STOP_TITLES = {
    "docs",
    "documentation",
    "home",
    "blog",
    "sign in",
    "pricing",
    "contact",
    "overview",
}


def _tokenize(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def _normalize_query(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _is_allowed(url: str, allowed_hosts: list[str]) -> bool:
    hostname = urlparse(url).hostname or ""
    return any(hostname.endswith(host) for host in allowed_hosts)


def _extract_results(html: str, source: dict[str, Any], query: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    query_tokens = _tokenize(query)
    compact_query = _normalize_query(query)
    candidates: list[tuple[int, dict[str, str]]] = []
    seen_urls: set[str] = set()

    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "").strip()
        if not href or href.startswith("#"):
            continue

        title = " ".join(anchor.stripped_strings)
        if len(title) < 4 or title.lower() in STOP_TITLES:
            continue

        url = urljoin(source["base_url"], href)
        if not _is_allowed(url, source["allowed_hosts"]):
            continue
        if url in seen_urls:
            continue

        surrounding_text = " ".join(anchor.parent.stripped_strings)
        summary = surrounding_text.replace(title, "", 1).strip(" -:|")
        summary = re.sub(r"\s+", " ", summary)
        haystack = " ".join([title, summary, url]).lower()
        score = 0

        if compact_query and compact_query in _normalize_query(haystack):
            score += 12
        if query_tokens:
            score += len(query_tokens & _tokenize(title)) * 10
            score += len(query_tokens & _tokenize(haystack)) * 3
        if any(segment in url for segment in ("/docs", "/reference", "/tutorial", "/manual", "/latest")):
            score += 3
        if not summary:
            summary = f"Official {urlparse(url).hostname} documentation entry related to '{query}'."

        if score > 0:
            seen_urls.add(url)
            candidates.append((score, {"title": title, "summary": summary, "source_url": url}))

    candidates.sort(key=lambda item: (-item[0], item[1]["title"]))
    return [payload for _, payload in candidates[:5]]


def _fallback_results(query: str) -> list[dict[str, str]]:
    return find_relevant_concepts(query, limit=5)


def search_docs(query: str, technology: str = "kubernetes") -> dict[str, Any]:
    """Search official docs for cloud-native technologies with local fallback."""

    search_query = (query or "").strip()
    tech = TECH_ALIASES.get((technology or "").strip().lower(), (technology or "").strip().lower())
    if not search_query:
        return {"success": False, "data": {}, "error": "Query must be a non-empty string."}
    if tech not in DOC_SOURCES:
        return {
            "success": False,
            "data": {"supported_technologies": sorted(DOC_SOURCES)},
            "error": f"Unsupported technology '{technology}'.",
        }

    cache_key = f"{tech}:{search_query.lower()}"
    if cache_key in SEARCH_CACHE:
        cached = SEARCH_CACHE[cache_key]
        data = {**cached, "cached": True}
        return {"success": True, "data": data, "error": None, **data}

    source = DOC_SOURCES[tech]
    try:
        response = httpx.get(
            source["search_url"].format(query=search_query),
            headers={"User-Agent": "CloudScope/1.0"},
            timeout=8.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        results = _extract_results(response.text, source, search_query)
        fallback_used = False
        if not results:
            results = _fallback_results(search_query)
            fallback_used = True
    except Exception:
        results = _fallback_results(search_query)
        fallback_used = True

    data = {
        "query": search_query,
        "technology": tech,
        "results": results,
        "cached": False,
        "fallback_used": fallback_used,
    }
    SEARCH_CACHE[cache_key] = data
    return {"success": True, "data": data, "error": None, **data}
