#-----------------------------------------------------------------------------
#	Spider / HTML parsing module: extracts image and page URLS from a page.
#-----------------------------------------------------------------------------

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".bmp")
SAFE_SCHEMES = {"http", "https"}
IGNORED_PREFIXES = ("data:", "javascript:", "mailto:", "tel:", "#")


#--------------
#	PUBLIC
#--------------

def extract_urls(html: bytes, base_url: str) -> tuple[set[str], set[str]]:
	"""
	Parses the HTML once.
	Returns (image_urls, page_urls), all absolute http(s) URLs.
	"""
	soup = BeautifulSoup(html, "lxml")
	images: set[str] = set()
	pages: set[str] = set()

	# <base href="..."> tags changes the base used to resolve relative links
	base_tag = soup.find("base", href=True)
	if base_tag is not None:
		base_url = _safe_resolve(base_tag.get("href"), base_url) or base_url

	# <img src="..."> tags
	for img in soup.find_all("img"):
		url = _safe_resolve(img.get("src"), base_url)
		if url is not None and _is_image(url):
			images.add(url)

	# <a href="..."> tags pointing directly to image files
	for link in soup.find_all("a"):
		url = _safe_resolve(link.get("href"), base_url)
		if url is not None:
			(images if _is_image(url) else pages).add(url)

	return images, pages


#--------------
#	PRIVATE
#--------------

def _is_image(url: str) -> bool:
	"""
	True if the URL path ends with an allowed image extension.
	"""
	return urlparse(url).path.lower().endswith(ALLOWED_EXTENSIONS)


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