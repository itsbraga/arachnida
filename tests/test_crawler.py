#------------------------------------------------------------------
#	Tests / BFS crawler on a fake website (no real network)
#
#	Site map:
#		/		-> img a.jpg			links: p1, p2, /, external
#		/p1		-> img a.jpg, b.jpg		links: p3, /
#		/p2		-> img c.jpg (same bytes as b.jpg)		links: p1
#		/p3		-> img d.jpg
#------------------------------------------------------------------

from dataclasses import dataclass, field
from pathlib import Path
import pytest

import spider.crawler as crawler
import spider.fetcher as fetcher
import spider.robots as robots
from spider.crawler import crawl


ROOT = "https://site.test/"

PAGES: dict[str, str] = {
	ROOT: '<img src="a.jpg"><a href="p1">1</a><a href="p2">2</a>'
		'<a href="/">home</a><a href="https://external.test/">ext</a>',
	ROOT + "p1": '<img src="a.jpg"><img src="b.jpg"><a href="p3">3</a><a href="/">home</a>',
	ROOT + "p2": '<img src="c.jpg"><a href="p1">1</a>',
	ROOT + "p3": '<img src="d.jpg">',
}

IMAGES: dict[str, bytes] = {
	ROOT + "a.jpg": b"\xff\xd8\xff" + b"A",
	ROOT + "b.jpg": b"\xff\xd8\xff" + b"B",
	ROOT + "c.jpg": b"\xff\xd8\xff" + b"B",		# same content as b.jpg
	ROOT + "d.jpg": b"\xff\xd8\xff" + b"D",
}


@dataclass
class FakeSite:
	"""
	What the fake network saw, in order, and the redirects it applies
	and the robots.txt it serves (absent by default: everything allowed).
	"""
	pages: list[str] = field(default_factory=list)
	images: list[str] = field(default_factory=list)
	redirects: dict[str, str] = field(default_factory=dict)
	robots: dict[str, tuple[int, bytes]] = field(default_factory=dict)


@pytest.fixture
def site(monkeypatch: pytest.MonkeyPatch) -> FakeSite:
	"""
	Replaces the network with the fake site.
	"""
	fake = FakeSite()

	def fake_fetch(url: str) -> tuple[bytes, str] | None:
		fake.pages.append(url)
		if url not in PAGES:
			return None
		return PAGES[url].encode(), fake.redirects.get(url, url)

	def fake_fetch_image(url: str) -> tuple[bytes, str] | None:
		fake.images.append(url)
		return IMAGES[url], "jpg"
	
	def fake_fetch_robots(url: str) -> tuple[int, bytes] | None:
		return fake.robots.get(url, (404, b""))

	monkeypatch.setattr(crawler, "fetch", fake_fetch)
	monkeypatch.setattr(crawler, "fetch_image", fake_fetch_image)
	monkeypatch.setattr(robots, "fetch_robots", fake_fetch_robots)
	monkeypatch.setattr(fetcher, "_delays", {})

	return fake


def test_without_recursion_only_start_page(site: FakeSite, tmp_path: Path):
	stats = crawl(ROOT, tmp_path, recursive=False, max_depth=5)
	assert site.pages == [ROOT]
	assert stats.saved == 1 and stats.pages == 1


def test_depth_one_visits_direct_links_only(site: FakeSite, tmp_path: Path):
	stats = crawl(ROOT, tmp_path, recursive=True, max_depth=1)
	assert site.pages == [ROOT, ROOT + "p1", ROOT + "p2"]
	assert stats.saved == 2						# a, b (c has the same bytes as b)
	assert stats.duplicates == 2				# a.jpg again on p1, c.jpg by hash
	assert len(list(tmp_path.iterdir())) == 2


def test_depth_two_reaches_p3(site: FakeSite, tmp_path: Path):
	stats = crawl(ROOT, tmp_path, recursive=True, max_depth=2)
	assert ROOT + "p3" in site.pages
	assert stats.saved == 3


def test_each_page_fetched_once_despite_cycles(site: FakeSite, tmp_path: Path):
	crawl(ROOT, tmp_path, recursive=True, max_depth=10)
	assert len(site.pages) == len(set(site.pages))


def test_never_leaves_the_site(site: FakeSite, tmp_path: Path):
	crawl(ROOT, tmp_path, recursive=True, max_depth=10)
	assert all(url.startswith(ROOT) for url in site.pages)


def test_image_url_downloaded_once(site: FakeSite, tmp_path: Path):
	crawl(ROOT, tmp_path, recursive=True, max_depth=10)
	assert len(site.images) == len(set(site.images))


def test_redirect_out_of_scope_is_skipped(site: FakeSite, tmp_path: Path):
	site.redirects[ROOT + "p2"] = "https://evil-corp.test/p2"
	stats = crawl(ROOT, tmp_path, recursive=True, max_depth=1)
	assert stats.saved == 2					# p2's image is never processed
	assert ROOT + "c.jpg" not in site.images


@pytest.mark.usefixtures("site")			# needed for its effect: the network is replaced
def test_unreachable_start_page(tmp_path: Path):
	stats = crawl("https://site.test/nowhere", tmp_path, recursive=True, max_depth=3)
	assert stats.pages == 0 and stats.saved == 0


@pytest.mark.usefixtures("site")
def test_ctrl_c_stops_cleanly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
	def interrupted(_url: str) -> tuple[bytes, str] | None:
		raise KeyboardInterrupt

	monkeypatch.setattr(crawler, "fetch_image", interrupted)
	stats = crawl(ROOT, tmp_path, recursive=True, max_depth=1)
	assert stats.interrupted


#--------------------
#	robots.txt
#--------------------

def test_disallowed_page_is_never_fetched(site: FakeSite, tmp_path: Path):
	site.robots[ROOT + "robots.txt"] = (200, b"User-agent: *\nDisallow: /p2")
	stats = crawl(ROOT, tmp_path, recursive=True, max_depth=1)
	assert site.pages == [ROOT, ROOT + "p1"]
	assert stats.blocked == 1


def test_disallowed_image_is_never_downloaded(site: FakeSite, tmp_path: Path):
	site.robots[ROOT + "robots.txt"] = (200, b"User-agent: *\nDisallow: /b.jpg")
	stats = crawl(ROOT, tmp_path, recursive=True, max_depth=1)
	assert ROOT + "b.jpg" not in site.images
	assert stats.blocked == 1


def test_robots_server_error_blocks_the_whole_site(site: FakeSite, tmp_path: Path):
	site.robots[ROOT + "robots.txt"] = (503, b"")
	stats = crawl(ROOT, tmp_path, recursive=True, max_depth=3)
	assert site.pages == []
	assert stats.pages == 0 and stats.blocked == 1


def test_redirect_to_disallowed_path_is_not_used(site: FakeSite, tmp_path: Path):
	site.robots[ROOT + "robots.txt"] = (200, b"User-agent: *\nDisallow: /forbidden")
	site.redirects[ROOT + "p2"] = ROOT + "forbidden"
	stats = crawl(ROOT, tmp_path, recursive=True, max_depth=1)
	assert ROOT + "c.jpg" not in site.images
	assert stats.blocked == 1