#-------------------------------------------------------------------
#	Spider / Fetcher module: single entry point for HTTP requests
#-------------------------------------------------------------------

import time
import requests
import urllib3

from common.colors import warn, error


USER_AGENT = "Arachnida/1.0 (School project)"	# to avoid 429 http error, add `; +contact_url`
REQUEST_DELAY = 0.5								# minimum seconds between the start of two requests
DEFAULT_TIMEOUT = 10							# seconds
MAX_HTML_BYTES = 10 * 1024 * 1024				# 10 MB safety cap

_session = requests.Session()					# reuses TCP/TLS connections between requests
_session.headers["User-Agent"] = USER_AGENT
_last_request = 0.0


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
	_throttle()

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


#--------------
#	PRIVATE
#--------------

def _throttle() -> None:
	"""
	Waits so that two requests start at least REQUEST_DELAY seconds apart.
	"""
	global _last_request

	elapsed = time.monotonic() - _last_request
	if elapsed < REQUEST_DELAY:
		time.sleep(REQUEST_DELAY - elapsed)

	_last_request = time.monotonic()


def _describe(e: Exception) -> str:
	if isinstance(e, requests.exceptions.Timeout):
		return "timeout"
	if isinstance(e, requests.exceptions.ConnectionError):
		return "connection error"
	if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
		return f"HTTP {e.response.status_code}"

	return f"request failed ({e})"