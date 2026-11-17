#--------------------------------------------------------------------------------------
#	Spider / BFS crawler: orchestrates fetch, parse, download across multiple pages.
#--------------------------------------------------------------------------------------

from pathlib import Path
from collections import deque

from spider.fetcher import fetch
from spider.parser import extract_image_urls, extract_page_links
from spider.downloader import download_image
from spider.url_utils import normalize, is_in_scope
from common.colors import info, warn


def crawl(start_url: str, dest_dir: Path, recursive: bool, max_depth: int) -> int:
	"""
	BFS crawl from start_url. Downloads images on each visited page.
	Stays within the same origin. Honours max_depth when recursive.
	Returns the amount of images successfully saved.
	"""
	root = normalize(start_url)

	queue: deque[tuple[str, int]] = deque([(root, 0)])
	visited: set[str] = {root}
	seen_hashes: set[str] = set()
	saved_count = 0

	while queue:
		url, depth = queue.popleft()
		info("crawler", f"depth={depth} visiting: {url}")

		page = fetch(url)
		if page is None:
			continue
		html, final_url = page

		final_url = normalize(final_url)
		if final_url != url:
			info("crawler", f"redirected: {url} -> {final_url}")
			if depth == 0:
				root = final_url	# the start URL itself moved: the scope follows it
			elif not is_in_scope(final_url, root):
				warn("crawler", f"redirected out of scope, skipped: {final_url}")
				continue
			elif final_url in visited:
				continue
			visited.add(final_url)

		# 1. Download every image on this page
		for image_url in sorted(extract_image_urls(html, final_url)):
			saved = download_image(image_url, dest_dir, seen_hashes)
			if saved:
				saved_count += 1
				info("crawler", f"saved: {saved}")

		# 2. Enqueue page links if we are still allowed to recurse
		if not recursive or depth >= max_depth:
			continue

		for link in extract_page_links(html, final_url):
			link_normalized = normalize(link)
			if link_normalized in visited:
				continue
			if not is_in_scope(link_normalized, root):
				continue
			visited.add(link_normalized)
			queue.append((link_normalized, depth + 1))

	return saved_count