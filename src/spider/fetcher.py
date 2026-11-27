#-------------------------------------------------------------------
#	Spider / Fetcher module: single entry point for HTTP requests
#-------------------------------------------------------------------

import time
import requests
import urllib3

from spider.url_utils import origin
from common.colors import warn, error


AGENT_TOKEN = "Arachnida"						# the name robots.txt groups are matched against
# to avoid 429 http error, add `; +contact_url`
USER_AGENT = f"{AGENT_TOKEN}/1.0 (School project)"
REQUEST_DELAY = 0.5								# minimum seconds between the start of two requests
MAX_CRAWL_DELAY = 10.0							# a robots.txt Crawl-delay is never honoured above this
DEFAULT_TIMEOUT = 10							# seconds
MAX_HTML_BYTES = 10 * 1024 * 1024				# 10 MB safety cap
MAX_ROBOTS_BYTES = 500 * 1024					# RFC 9309: parsers must read at least 500 KiB

_session = requests.Session()					# reuses TCP/TLS connections between requests
_session.headers["User-Agent"] = USER_AGENT
_last_request = 0.0
_delays: dict[str, float] = {}					# origin -> delay asked by its robots.txt


#--------------
#	PUBLIC
#--------------

def fetch(url: str) -> tuple[bytes, str] | None:
	"""
	Fetches an HTML page.
	Returns (html, final_url) on success, None on any error or rejection.
	"""
	return http_get(url, MAX_HTML_BYTES, html_only=True)


def http_get(url: str, max_bytes: int, html_only: bool = False) -> tuple[bytes, str] | None:
	"""
	Every network request goes through here: throttled, size-capped, connection
	always released.
	Returns (content, final_url), None on any error or rejection.
	final_url differs from url when the server redirected the request.
	"""
	_throttle(url)

	try:
		with _session.get(url, timeout=DEFAULT_TIMEOUT, stream=True) as response:
			response.raise_for_status()		# converts a 4xx/5xx code into an exception
			content_type = response.headers.get("Content-Type", "")
			if html_only and "text/html" not in content_type.lower():
				warn("fetcher", f"not HTML ({content_type}): {url}")
				return None
			content = response.raw.read(max_bytes + 1, decode_content=True)
			final_url = response.url
	except (requests.exceptions.RequestException, urllib3.exceptions.HTTPError, OSError) as e:
		error("fetcher", f"{_describe(e)}: {url}")
		return None

	if len(content) > max_bytes:
		warn("fetcher", f"too large (>{max_bytes} bytes): {url}")
		return None

	return content, final_url


def fetch_robots(url: str) -> tuple[int, bytes] | None:
	"""
	Fetches a robots.txt file.
	Returns (status, body) for any HTTP status, None if the server is unreachable.
	Unlike http_get, a 4xx or 5xx is not an error here: it carries meaning.
	A file over the cap is truncated, not rejected: RFC 9309 allows ignoring the rest.
	"""
	_throttle(url)

	try:
		with _session.get(url, timeout=DEFAULT_TIMEOUT, stream=True) as response:
			body = response.raw.read(MAX_ROBOTS_BYTES, decode_content=True)
			return response.status_code, body
	except (requests.exceptions.RequestException, urllib3.exceptions.HTTPError, OSError) as e:
		error("fetcher", f"{_describe(e)}: {url}")
		return None


def set_crawl_delay(site: str, seconds: float) -> None:
	"""
	Applies a robots.txt Crawl-delay to every later request to that origin,
	never below REQUEST_DELAY nor above MAX_CRAWL_DELAY.
	"""
	_delays[site] = min(max(seconds, REQUEST_DELAY), MAX_CRAWL_DELAY)


#--------------
#	PRIVATE
#--------------

def _throttle(url: str) -> None:
	"""
	Waits so that two requests start at least the delay of the target origin apart.
	The wait is measured from the last request to any host: sometimes longer than
	needed, never shorter.
	"""
	global _last_request

	delay = _delays.get(origin(url), REQUEST_DELAY)
	elapsed = time.monotonic() - _last_request
	if elapsed < delay:
		time.sleep(delay - elapsed)

	_last_request = time.monotonic()


def _describe(e: Exception) -> str:
	if isinstance(e, requests.exceptions.Timeout):
		return "timeout"
	if isinstance(e, requests.exceptions.ConnectionError):
		return "connection error"
	if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
		return f"HTTP {e.response.status_code}"

	return f"request failed ({e})"