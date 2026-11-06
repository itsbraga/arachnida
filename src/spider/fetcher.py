import sys
import requests

USER_AGENT = "Arachnida/1.0 (42 school project)"
DEFAULT_TIMEOUT = 10 	# seconds


def fetch(url: str, timeout: int = DEFAULT_TIMEOUT) -> str | None:
	"""
	Fetches the content of a URL as text
	Returns the HTML string on success, None on any error
	"""
	headers = {"User-Agent": USER_AGENT}

	try:
		response = requests.get(url, headers=headers, timeout=timeout)
		response.raise_for_status()		# converts a 4xx/5xx code into an exception
	except requests.exceptions.Timeout:
		print(f"[fetcher] timeout: {url}", file=sys.stderr)
		return None
	except requests.exceptions.ConnectionError:
		print(f"[fetcher] connection error: {url}", file=sys.stderr)
		return None
	except requests.exceptions.HTTPError as e:
		print(f"[fetcher] HTTP {e.response.status_code}: {url}", file=sys.stderr)
		return None
	except requests.exceptions.RequestException as e:
		print(f"[fetcher] error: {url} - {e}", file=sys.stderr)
		return None

	content_type = response.headers.get("Content-Type", "")
	if "text/html" not in content_type.lower():
		print(f"[fetcher] not HTML ({content_type}): {url}", file=sys.stderr)
		return None

	return response.text