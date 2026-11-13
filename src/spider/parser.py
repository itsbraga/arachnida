#--------------------------------------------------------------------------
#	Spider / HTML parsing module: Extracts image URLs from an HTML page.
#--------------------------------------------------------------------------

from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}
SAFE_SCHEMES = {"http", "https"}
IGNORED_PREFIXES = ("data:", "javascript:", "mailto:", "tel:", "#")


#--------------
#	PUBLIC
#--------------

def extract_image_urls(html: str, base_url: str) -> set[str]:
	"""
	Parses the HTML and returns the set of absolute image URLS found.
	"""
	soup = BeautifulSoup(html, "lxml")
	urls: set[str] = set()

	# <img src="..."> tags
	for img in soup.find_all("img"):
		_try_add_image(img.get("src"), base_url, urls)

	# <a href="..."> tags pointing directly to image files
	for link in soup.find_all("a"):
		_try_add_image(link.get("href"), base_url, urls)

	return urls


def extract_page_links(html: str, base_url: str) -> set[str]:
	"""
	Parses the HTML and returns the set of absolute page URLs (<a href>)
	that look like navigable pages (not images, not downloads).
	"""
	soup = BeautifulSoup(html, "lxml")
	urls: set[str] = set()

	for link in soup.find_all("a"):
		_try_add_page(link.get("href"), base_url, urls)

	return urls


#--------------
#	PRIVATE
#--------------

def _safe_resolve(raw: object, base_url: str) -> str | None:
	"""
	Shared guarded URL resolution.
	Returns None on any rejection.
	"""
	if not isinstance(raw, str):
		return None

	raw = raw.strip()
	if not raw:
		return None
	if raw.lower().startswith(IGNORED_PREFIXES):
		return None

	try:
		absolute = urljoin(base_url, raw)
	except (ValueError, TypeError):
		return None

	if urlparse(absolute).scheme not in SAFE_SCHEMES:
		return None

	return absolute


def _try_add_image(raw: object, base_url: str, urls: set[str]) -> None:
	"""
	Safely adds raw to urls if it resolves to an image URL.
	"""
	absolute = _safe_resolve(raw, base_url)
	if absolute is None:
		return

	path = urlparse(absolute).path.lower()
	if any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS):
		urls.add(absolute)


def _try_add_page(raw: object, base_url: str, urls: set[str]) -> None:
	"""
	Safely adds raw to urls if it resolves to a navigable page URL.
	"""
	absolute = _safe_resolve(raw, base_url)
	if absolute is None:
		return

	path = urlparse(absolute).path.lower()
	# Exclude anything that looks like an image or a non-page asset
	if any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS):
		return
	urls.add(absolute)