#------------------------------
#	Spider / Fetcher module
#------------------------------

import requests
from common.colors import warn, error


USER_AGENT = "Arachnida/1.0 (School project)"
DEFAULT_TIMEOUT = 10 	# seconds


def fetch(url: str, timeout: int = DEFAULT_TIMEOUT) -> str | None:
	"""
	Fetches the content of a URL as text.
	Returns the HTML string on success, None on any error.
	"""
	headers = {"User-Agent": USER_AGENT}

	try:
		response = requests.get(url, headers=headers, timeout=timeout)
		response.raise_for_status()		# converts a 4xx/5xx code into an exception
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

	content_type = response.headers.get("Content-Type", "")
	if "text/html" not in content_type.lower():
		warn("fetcher", f"not HTML ({content_type}): {url}")
		return None

	return response.text