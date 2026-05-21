from __future__ import annotations

import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Iterable

_API_URL = "https://export.arxiv.org/api/query"
_ATOM_NAMESPACE = {"atom": "http://www.w3.org/2005/Atom"}
_USER_AGENT = "voidful-wordcloud/1.0 (+https://github.com/voidful/voidful)"
_WHITESPACE = re.compile(r"\s+")
_SORT_CRITERIA = {"lastUpdatedDate", "submittedDate", "relevance"}
_MAX_PAGE_SIZE = 2000


def query(
    search_query: str | Iterable[str],
    start_index: int = 0,
    max_index: int = 500,
    results_per_iteration: int = 100,
    wait_time: float = 3.0,
    sort_by: str = "lastUpdatedDate",
    timeout: float = 30.0,
    retries: int = 3,
) -> list[dict[str, str]]:
    """Fetch arXiv papers and return the old arxivpy-shaped records.

    Keeping this adapter local gives the wordcloud script a stable contract
    without depending on an unmaintained third-party arXiv wrapper.
    """
    if start_index < 0 or max_index < 0:
        raise ValueError("arXiv indexes must be non-negative")
    if max_index <= start_index:
        return []
    if results_per_iteration <= 0:
        raise ValueError("results_per_iteration must be positive")
    if wait_time < 0:
        raise ValueError("wait_time must be non-negative")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if retries < 0:
        raise ValueError("retries must be non-negative")
    if sort_by not in _SORT_CRITERIA:
        raise ValueError(f"Unsupported arXiv sort criterion: {sort_by}")

    articles: list[dict[str, str]] = []
    query_string = _build_query(search_query)
    cursor = start_index

    while cursor < max_index:
        if articles and wait_time > 0:
            time.sleep(wait_time)

        page_size = min(results_per_iteration, max_index - cursor, _MAX_PAGE_SIZE)
        page = _fetch_page(
            query_string=query_string,
            start=cursor,
            max_results=page_size,
            sort_by=sort_by,
            wait_time=wait_time,
            timeout=timeout,
            retries=retries,
        )
        page_articles = _parse_page(page)
        if not page_articles:
            break

        articles.extend(page_articles)
        cursor += len(page_articles)

        if len(page_articles) < page_size:
            break

    return articles


def _build_query(search_query: str | Iterable[str]) -> str:
    if isinstance(search_query, str):
        search_query = [search_query]

    terms = [term.strip() for term in search_query if term.strip()]
    if not terms:
        return ""
    return " AND ".join(_normalize_term(term) for term in terms)


def _normalize_term(term: str) -> str:
    if ":" in term:
        return term
    if re.fullmatch(r"[a-z-]+\.[A-Z]{2}(?:\.[A-Z]{2})?", term):
        return f"cat:{term}"
    return f"all:{term}"


def _fetch_page(
    query_string: str,
    start: int,
    max_results: int,
    sort_by: str,
    wait_time: float,
    timeout: float,
    retries: int,
) -> bytes:
    params = urllib.parse.urlencode(
        {
            "search_query": query_string,
            "start": start,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": "descending",
        }
    )
    request = urllib.request.Request(
        f"{_API_URL}?{params}",
        headers={"User-Agent": _USER_AGENT},
    )

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if not _should_retry_http(error.code, attempt, retries):
                raise
            _sleep_before_retry(error, attempt, wait_time)
        except (TimeoutError, urllib.error.URLError, socket.timeout):
            if attempt >= retries:
                raise
            _sleep_before_retry(None, attempt, wait_time)

    raise RuntimeError("arXiv page fetch failed without an exception")


def _should_retry_http(status_code: int, attempt: int, retries: int) -> bool:
    return attempt < retries and (status_code == 429 or 500 <= status_code < 600)


def _sleep_before_retry(
    error: urllib.error.HTTPError | None,
    attempt: int,
    wait_time: float,
) -> None:
    retry_after = None
    if error is not None:
        retry_after = error.headers.get("Retry-After")

    try:
        if retry_after:
            delay = float(retry_after)
        elif error is not None and error.code == 429:
            delay = max(30.0, wait_time * (attempt + 1) * 5)
        else:
            delay = wait_time * (attempt + 1)
    except ValueError:
        delay = wait_time * (attempt + 1)

    time.sleep(max(delay, wait_time, 1.0))


def _parse_page(page: bytes) -> list[dict[str, str]]:
    root = ET.fromstring(page)
    articles = []

    for entry in root.findall("atom:entry", _ATOM_NAMESPACE):
        title = entry.findtext("atom:title", default="", namespaces=_ATOM_NAMESPACE)
        abstract = entry.findtext("atom:summary", default="", namespaces=_ATOM_NAMESPACE)
        articles.append(
            {
                "title": _normalize(title),
                "abstract": _normalize(abstract),
            }
        )

    return articles


def _normalize(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()
