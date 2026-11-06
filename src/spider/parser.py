"""
Spider / HTML parsing module: Extracts image URLs from an HTML page
"""

from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}
SAFE_SCHEMES = {"http", "https"}
IGNORED_PREFIXES = ("data:", "javascript:", "mailto:", "tel:", "#")


def _try_add(raw: object, base_url: str, urls: set[str]) -> None:
	"""
	Safety resolves a raw attribute value and adds it to urls if it
	looks like an image.
	"""
	if not isinstance(raw, str):
		return

	raw = raw.strip()
	if not raw:
		return
	if raw.lower().startswith(IGNORED_PREFIXES):
		return

	try:
		absolute = urljoin(base_url, raw)
	except (ValueError, TypeError):
		return

	parsed = urlparse(absolute)
	if parsed.scheme not in SAFE_SCHEMES:
		return

	path = parsed.path.lower()
	if any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS):
		urls.add(absolute)


def extract_image_urls(html: str, base_url: str) -> set[str]:
	"""
	Parses the HTML and returns the set of absolute image URLS found.
	"""
	soup = BeautifulSoup(html, "lxml")
	urls: set[str] = set()

	# <img src="..."> tags
	for img in soup.find_all("img"):
		_try_add(img.get("src"), base_url, urls)

	# <a href="..."> tags pointing directly to image files
	for link in soup.find_all("a"):
		_try_add(link.get("href"), base_url, urls)

	return urls