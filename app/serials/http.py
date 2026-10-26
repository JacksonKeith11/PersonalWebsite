import calendar
import time

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)


def client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
        follow_redirects=True,
        timeout=45,
    )


def get(c: httpx.Client, url: str, retries: int = 4, **kwargs) -> httpx.Response:
    """GET with backoff on rate limiting, timeouts, and transient server errors."""
    for attempt in range(retries):
        try:
            r = c.get(url, **kwargs)
        except httpx.TransportError:
            if attempt == retries - 1:
                raise
            time.sleep(10 * (attempt + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            wait = int(r.headers.get("Retry-After", "0") or 0) or 10 * (attempt + 1)
            time.sleep(min(wait, 120))
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()
    return r


def struct_to_epoch(t) -> float | None:
    return float(calendar.timegm(t)) if t else None
