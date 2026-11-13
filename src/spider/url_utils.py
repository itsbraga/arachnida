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
		parsed.path, parsed.params, parsed.query, ""
	))


def is_in_scope(url: str, root_url: str) -> bool:
	"""
	True if url shares scheme + host + port with root_url
	Same-origin policy -> prevents the crawler from leaving the site
	"""
	a = urlparse(url)
	b = urlparse(root_url)

	return (
		a.scheme.lower() == b.scheme.lower()
		and a.netloc.lower() == b.netloc.lower()
	)