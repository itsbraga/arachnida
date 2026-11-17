#------------------------------
#	Spider / Fetcher module
#------------------------------

import requests
import urllib3
from common.colors import warn, error


USER_AGENT = "Arachnida/1.0 (School project)"
DEFAULT_TIMEOUT = 10				# seconds
MAX_HTML_BYTES = 10 * 1024 * 1024	# 10 MB safety cap


def fetch(url: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[bytes, str] | None:
	"""
	Fetches an HTML page.
	Returns (content, final_url) on success, None on any error or rejection.
	final_url differs from url when the server redirected the request.
	"""
	headers = {"User-Agent": USER_AGENT}

	try:
		with requests.get(url, headers=headers, timeout=timeout, stream=True) as response:
			response.raise_for_status()		# converts a 4xx/5xx code into an exception

			content_type = response.headers.get("Content-Type", "")
			if "text/html" not in content_type.lower():
				warn("fetcher", f"not HTML ({content_type}): {url}")
				return None

			content = response.raw.read(MAX_HTML_BYTES + 1, decode_content=True)
			final_url = response.url
	except requests.exceptions.Timeout:
		error("fetcher", f"timeout: {url}")
		return None
	except requests.exceptions.ConnectionError:
		error("fetcher", f"connection error: {url}")
		return None
	except requests.exceptions.HTTPError as e:
		status_code = e.response.status_code if e.response is not None else "unknown"
		error("fetcher", f"HTTP {status_code}: {url}")
		return None
	except requests.exceptions.RequestException as e:
		error("fetcher", f"{url} - {e}")
		return None
	except (urllib3.exceptions.HTTPError, OSError) as e:
		error("fetcher", f"read failed: {url} - {e}")
		return None

	if len(content) > MAX_HTML_BYTES:
		warn("fetcher", f"page too large (> {MAX_HTML_BYTES} bytes): {url}")
		return None

	return content, final_url