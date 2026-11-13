#--------------------------------------------------------------------------------------
#	Spider / BFS crawler: orchestrates fetch, parse, download across multiple pages.
#--------------------------------------------------------------------------------------

from collections import deque
from pathlib import Path

from spider.fetcher import fetch
from spider.parser import extract_image_urls, extract_page_links
from spider.downloader import download_image
from spider.url_utils import normalize, is_in_scope
from common.colors import info


def crawl(start_url: str, dest_dir: Path, recursive: bool, max_depth: int) -> int:
	"""
	BFS crawl from start_url. Downloads images on each visited page.
	Stays within the same origin. Honours max_depth when recursive.
	Returns the amount of images successfully saved.
	"""
	start_normalized = normalize(start_url)

	queue: deque[tuple[str, int]] = deque([(start_normalized, 0)])
	visited: set[str] = {start_normalized}
	seen_hashes: set[str] = set()
	saved_count = 0

	while queue:
		url, depth = queue.popleft()
		info("crawler", f"depth={depth} visiting: {url}")

		html = fetch(url)
		if html is None:
			continue

		# 1. Download every image on this page
		for image_url in sorted(extract_image_urls(html, url)):
			saved = download_image(image_url, dest_dir, seen_hashes)
			if saved:
				saved_count += 1
				info("crawler", f"saved: {saved}")

		# 2. Enqueue page links if we are still allowed to recurse
		if not recursive or depth >= max_depth:
			continue

		for link in extract_page_links(html, url):
			link_normalized = normalize(link)
			if link_normalized in visited:
				continue
			if not is_in_scope(link_normalized, start_normalized):
				continue
			visited.add(link_normalized)
			queue.append((link_normalized, depth + 1))

	return saved_count