"""Deterministic publication and claim identity helpers."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "igshid",
    "si",
    "ref",
    "ref_src",
}

DOI_RE = re.compile(
    r"(?:doi\.org/|doi:\s*)(10\.\d{4,9}/[-._;()/:A-Z0-9]+)",
    re.IGNORECASE,
)
ARXIV_RE = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf)/|arxiv:\s*)(\d{4}\.\d{4,5})(?:v\d+)?",
    re.IGNORECASE,
)
ARXIV_OLD_RE = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf)/|arxiv:\s*)([a-z\-]+/\d{7})(?:v\d+)?",
    re.IGNORECASE,
)

SIMILARITY_THRESHOLD = 0.92


def normalise_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def normalise_title(title: str) -> str:
    text = normalise_whitespace(title)
    text = re.sub(r"[\"'`]", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return normalise_whitespace(text)


def normalise_claim(claim: str) -> str:
    return normalise_whitespace(claim)


def extract_doi(url_or_text: str) -> str | None:
    match = DOI_RE.search(url_or_text or "")
    if not match:
        return None
    return match.group(1).rstrip(".").lower()


def extract_arxiv_id(url_or_text: str) -> str | None:
    text = url_or_text or ""
    match = ARXIV_RE.search(text)
    if match:
        return match.group(1).lower()
    match = ARXIV_OLD_RE.search(text)
    if match:
        return match.group(1).lower()
    return None


def normalise_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path.rstrip("/")
    # Drop tracking query params; keep meaningful ones sorted.
    kept = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS
    ]
    kept.sort()
    query = urlencode(kept)
    # Ignore fragments
    return urlunparse((scheme, netloc, path, "", query, ""))


def publication_keys(row: dict[str, str]) -> set[str]:
    keys: set[str] = set()
    url = row.get("source_url") or ""
    title = row.get("source_title") or ""
    doi = extract_doi(url) or extract_doi(title)
    if doi:
        keys.add(f"doi:{doi}")
    arxiv = extract_arxiv_id(url)
    if arxiv:
        keys.add(f"arxiv:{arxiv}")
    norm_url = normalise_url(url)
    if norm_url:
        keys.add(f"url:{norm_url}")
    norm_title = normalise_title(title)
    if norm_title:
        keys.add(f"title:{norm_title}")
    return keys


def claim_key(row: dict[str, str]) -> str:
    return normalise_claim(row.get("talking_point") or "")


def claims_similar(a: str, b: str, threshold: float = SIMILARITY_THRESHOLD) -> bool:
    na, nb = normalise_claim(a), normalise_claim(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    return SequenceMatcher(None, na, nb).ratio() >= threshold


def share_publication(a: dict[str, str], b: dict[str, str]) -> bool:
    ka, kb = publication_keys(a), publication_keys(b)
    if not ka or not kb:
        return False
    # Prefer strong identifiers
    strong_a = {k for k in ka if k.startswith(("doi:", "arxiv:", "url:"))}
    strong_b = {k for k in kb if k.startswith(("doi:", "arxiv:", "url:"))}
    if strong_a and strong_b and strong_a & strong_b:
        return True
    title_a = {k for k in ka if k.startswith("title:")}
    title_b = {k for k in kb if k.startswith("title:")}
    return bool(title_a and title_b and title_a & title_b)
