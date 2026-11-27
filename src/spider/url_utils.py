#------------------------------------------
#	Spider / URL manipulation utilities
#------------------------------------------

from urllib.parse import urlparse, urlunparse


def normalize(url: str) -> str:
	"""
	Canonicalises a URL for deduplication purposes
		- lowercases scheme and host
		- strips fragment (#section)
		- leaves path/query intact
	"""
	parsed = urlparse(url)

	return urlunparse((
		parsed.scheme.lower(), parsed.netloc.lower(),
		parsed.path or "/", parsed.params, parsed.query, ""
	))


def origin(url: str) -> str:
	"""
	"https://Site.com:8443/a/b?q" -> "https://site.com:8443"
	The unit that the crawl scope, robots.txt and Crawl-delay apply to.
	"""
	parsed = urlparse(url)

	return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def is_in_scope(url: str, root_url: str) -> bool:
	"""
	True if url shares scheme + host + port with root_url
	Same-origin policy -> prevents the crawler from leaving the site
	"""
	return origin(url) == origin(root_url)