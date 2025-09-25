from __future__ import annotations

from typing import Any
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


def add(a: int, b: int) -> int:
    """Add two integers and return the result.

    Args:
        a: First integer.
        b: Second integer.

    Returns:
        Sum of a and b.
    """

    return a + b


def subtract(a: int, b: int) -> int:
    """Subtract two integers and return the result (a - b).

    Args:
        a: Minuend integer.
        b: Subtrahend integer.

    Returns:
        Difference a - b.
    """

    return a - b


def multiply(a: int, b: int) -> int:
    """Multiply two integers and return the result.

    Args:
        a: First integer.
        b: Second integer.

    Returns:
        Product a * b.
    """

    return a * b


def divide(a: int, b: int) -> float:
    """Divide two integers and return the result as float.

    Args:
        a: Dividend integer.
        b: Divisor integer (must be non-zero).

    Returns:
        Quotient a / b as float.

    Raises:
        ValueError: If b == 0.
    """

    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b


def modulus(a: int, b: int) -> int:
    """Compute remainder of a divided by b (a % b).

    Args:
        a: Dividend integer.
        b: Divisor integer (must be non-zero).

    Returns:
        Remainder a % b.

    Raises:
        ValueError: If b == 0.
    """

    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a % b


def _http_get(url: str, timeout: float = 10.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "ragbits-agents/extra-tools"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def arxiv_search(query: str, max_results: int = 3) -> dict[str, Any]:
    """Search arXiv and return up to `max_results` entries.

    Args:
        query: Search query (e.g., "quantum computing")
        max_results: Max number of results to return (default 3)

    Returns:
        Dict with a list of results: title, summary, link.
    """

    if max_results <= 0:
        return {"results": []}

    base = "https://export.arxiv.org/api/query"
    params = {
        "search_query": urllib.parse.quote_plus(query),
        "start": "0",
        "max_results": str(max_results),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    url = f"{base}?search_query={params['search_query']}&start={params['start']}&max_results={params['max_results']}&sortBy={params['sortBy']}&sortOrder={params['sortOrder']}"

    raw = _http_get(url)
    root = ET.fromstring(raw)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    results: list[dict[str, str]] = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        summary_el = entry.find("atom:summary", ns)
        link_el = entry.find("atom:link[@rel='alternate']", ns)
        title = (title_el.text or "").strip() if title_el is not None else ""
        summary = (summary_el.text or "").strip() if summary_el is not None else ""
        link = link_el.get("href") if link_el is not None else ""
        # Trim overly long summaries for brevity
        if len(summary) > 1200:
            summary = summary[:1200] + "..."
        results.append({"title": title, "summary": summary, "link": link})

    return {"results": results}


def wiki_search(query: str, max_results: int = 2, language: str = "en") -> dict[str, Any]:
    """Search Wikipedia and return up to `max_results` entries with extracts.

    Args:
        query: Search query (e.g., "Alan Turing")
        max_results: Max number of results (default 2)
        language: Wikipedia language code (default "en")

    Returns:
        Dict with list of results: title, pageid, extract, url.
    """

    if max_results <= 0:
        return {"results": []}

    api = f"https://{language}.wikipedia.org/w/api.php"
    search_params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": str(max_results),
        "format": "json",
    }
    search_url = f"{api}?{urllib.parse.urlencode(search_params)}"
    raw = _http_get(search_url)
    data = json.loads(raw.decode("utf-8"))
    hits = data.get("query", {}).get("search", [])
    if not hits:
        return {"results": []}

    page_ids = [str(h.get("pageid")) for h in hits if "pageid" in h]
    extract_params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": "1",
        "exintro": "1",
        "pageids": "|".join(page_ids),
        "format": "json",
    }
    extract_url = f"{api}?{urllib.parse.urlencode(extract_params)}"
    raw2 = _http_get(extract_url)
    data2 = json.loads(raw2.decode("utf-8"))
    pages = data2.get("query", {}).get("pages", {})

    results: list[dict[str, Any]] = []
    for pid in page_ids:
        page = pages.get(pid)
        if not page:
            continue
        title = page.get("title", "")
        extract = (page.get("extract", "") or "").strip()
        if len(extract) > 1200:
            extract = extract[:1200] + "..."
        url = f"https://{language}.wikipedia.org/?curid={pid}"
        results.append({"title": title, "pageid": int(pid), "extract": extract, "url": url})

    return {"results": results}


def get_extra_instruction_tpl() -> str:
    """Generate tool usage instructions template for arithmetic and lookups.

    Returns:
        Instruction template string to include in system prompts.
    """

    return (
        "\n\n"
        "## Tools Workflow (Arithmetic, arXiv, Wikipedia)\n\n"
        "Available actions:\n"
        "- `add(a, b)`, `subtract(a, b)`, `multiply(a, b)`, `divide(a, b)`, `modulus(a, b)`\n"
        "- `arxiv_search(query, max_results=3)`\n"
        "- `wiki_search(query, max_results=2, language='en')`\n\n"
        "POLICY:\n"
        "1) Use arithmetic tools for calculations instead of inline math when non-trivial.\n"
        "2) Use arXiv/Wikipedia tools when scholarly/general knowledge retrieval is needed.\n"
        "3) Keep outputs concise; provide FINAL ANSWER after any intermediate reasoning.\n"
    )