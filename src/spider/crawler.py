#--------------------------------------------------------------------------------------
#	Spider / BFS crawler: orchestrates fetch, parse, download across multiple pages.
#--------------------------------------------------------------------------------------

from dataclasses import dataclass
from pathlib import Path
from collections import deque
import hashlib

from spider.fetcher import fetch
from spider.parser import extract_urls
from spider.downloader import fetch_image, save_image
from spider.url_utils import normalize, is_in_scope
from common.colors import info, warn


@dataclass
class CrawlStats:
	saved: int = 0
	duplicates: int = 0
	pages: int = 0
	interrupted: bool = False


#--------------
#	PUBLIC
#--------------

def crawl(start_url: str, dest_dir: Path, recursive: bool, max_depth: int) -> CrawlStats:
	"""
	BFS crawl from start_url. Downloads images on each visited page.
	Stays within the same origin. Honours max_depth when recursive.
	"""
	crawler = _Crawler(start_url, dest_dir, max_depth if recursive else 0)

	try:
		crawler.run()
	except KeyboardInterrupt:
		warn("crawler", "interrupted by user")
		crawler.stats.interrupted = True

	return crawler.stats


#--------------
#	PRIVATE
#--------------

class _Crawler:

	def __init__(self, start_url: str, dest_dir: Path, max_depth: int) -> None:
		self.root = normalize(start_url)
		self.dest_dir = dest_dir
		self.max_depth = max_depth
		self.queue: deque[tuple[str, int]] = deque([(self.root, 0)])
		self.visited: set[str] = {self.root}
		self.seen_urls: set[str] = set()
		self.seen_hashes: set[str] = set()
		self.stats = CrawlStats()


	def run(self) -> None:
		while self.queue:
			url, depth = self.queue.popleft()
			info("crawler", f"depth={depth} visiting: {url}")

			page = self._fetch_page(url, depth)
			if page is None:
				continue
			html, final_url = page

			images, links = extract_urls(html, final_url)

			for image_url in sorted(images):
				self._handle_image(image_url)

			if depth < self.max_depth:
				self._enqueue(links, depth + 1)


	def _fetch_page(self, url: str, depth: int) -> tuple[bytes, str] | None:
		"""
		Fetches a page and handles redirects.
		Returns (html, final_url), or None if the page must be skipped.
		"""
		page = fetch(url)
		if page is None:
			return None

		html, final_url = page
		final_url = normalize(final_url)

		if final_url != url:
			info("crawler", f"redirected: {url} -> {final_url}")
			if depth == 0:
				self.root = final_url	# the start URL itself moved: the scope follows it
			elif not is_in_scope(final_url, self.root):
				warn("crawler", f"redirected out of scope, skipped: {final_url}")
				return None
			elif final_url in self.visited:
				return None
			self.visited.add(final_url)

		self.stats.pages += 1

		return html, final_url


	def _handle_image(self, image_url: str) -> None:
		"""
		Downloads and saves one image, unless its URL or content was already seen.
		"""
		if image_url in self.seen_urls:
			self.stats.duplicates += 1
			return
		self.seen_urls.add(image_url)

		image = fetch_image(image_url)
		if image is None:
			return
		content, fmt = image

		content_hash = hashlib.sha256(content).hexdigest()
		if content_hash in self.seen_hashes:
			self.stats.duplicates += 1
			return

		saved = save_image(content, fmt, image_url, self.dest_dir)
		if saved is not None:
			self.seen_hashes.add(content_hash)
			self.stats.saved += 1
			info("crawler", f"saved: {saved}")


	def _enqueue(self, links: set[str], depth: int) -> None:
		"""
		Queues unvisited same-origin links, in a stable order.
		"""
		for link in sorted(links):
			normalized = normalize(link)
			if normalized in self.visited or not is_in_scope(normalized, self.root):
				continue
			self.visited.add(normalized)
			self.queue.append((normalized, depth))