#--------------------------------------------------------------------
#	Tests / robots.txt parsing and matching (RFC 9309), no network
#--------------------------------------------------------------------

import time

import pytest

import spider.fetcher as fetcher
import spider.robots as robots
from spider.robots import RobotRules, RobotsCache, parse_robots


AGENT = "Arachnida"
SITE = "https://site.test"


def _rules(text: str) -> RobotRules:
	return parse_robots(text, AGENT)


def _allowed(text: str, path: str) -> bool:
	return _rules(text).allows(SITE + path)


#--------------------
#	Group selection
#--------------------

def test_no_file_content_allows_everything():
	assert _allowed("", "/anything")


def test_star_group_applies_by_default():
	assert not _allowed("User-agent: *\nDisallow: /private/", "/private/x")


def test_specific_group_replaces_star_group():
	text = "User-agent: *\nDisallow: /\n\nUser-agent: Arachnida\nDisallow: /secret/"
	assert _allowed(text, "/page")				# the '*' rules do not apply to us
	assert not _allowed(text, "/secret/a")


def test_agent_name_is_case_insensitive_and_ignores_version():
	assert not _allowed("User-agent: arachnida/2.0\nDisallow: /", "/")


def test_other_agents_rules_are_ignored():
	assert _allowed("User-agent: Googlebot\nDisallow: /", "/page")


def test_groups_for_the_same_agent_are_merged():
	text = "User-agent: Arachnida\nDisallow: /a\n\nUser-agent: Arachnida\nDisallow: /b"
	assert not _allowed(text, "/a") and not _allowed(text, "/b")


def test_several_agents_share_one_group():
	text = "User-agent: Googlebot\nUser-agent: Arachnida\nDisallow: /shared"
	assert not _allowed(text, "/shared")


def test_user_agent_after_rules_starts_a_new_group():
	text = "User-agent: Arachnida\nDisallow: /a\nUser-agent: Googlebot\nDisallow: /b"
	assert not _allowed(text, "/a")
	assert _allowed(text, "/b")


#--------------------
#	Rule matching
#--------------------

def test_disallow_is_a_prefix_match():
	text = "User-agent: *\nDisallow: /admin"
	assert not _allowed(text, "/admin")
	assert not _allowed(text, "/admin/users")
	assert not _allowed(text, "/administrator")
	assert _allowed(text, "/public/admin")


def test_empty_disallow_allows_everything():
	assert _allowed("User-agent: *\nDisallow:", "/anything")


def test_longest_match_wins():
	text = "User-agent: *\nDisallow: /private/\nAllow: /private/public.html"
	assert _allowed(text, "/private/public.html")
	assert not _allowed(text, "/private/other.html")


def test_rule_order_does_not_matter():
	text = "User-agent: *\nAllow: /private/public.html\nDisallow: /private/"
	assert _allowed(text, "/private/public.html")


def test_allow_wins_on_equal_length():
	assert _allowed("User-agent: *\nDisallow: /page\nAllow: /page", "/page")


def test_star_wildcard():
	text = "User-agent: *\nDisallow: /*.php"
	assert not _allowed(text, "/index.php")
	assert not _allowed(text, "/dir/page.php?id=1")
	assert _allowed(text, "/index.html")


def test_dollar_anchors_the_end():
	text = "User-agent: *\nDisallow: /*.php$"
	assert not _allowed(text, "/index.php")
	assert _allowed(text, "/index.php?id=1")
	assert _allowed(text, "/index.php5")


def test_query_string_is_part_of_the_target():
	assert not _allowed("User-agent: *\nDisallow: /search?q=", "/search?q=spider")


def test_robots_txt_itself_is_always_allowed():
	assert _allowed("User-agent: *\nDisallow: /", "/robots.txt")


def test_non_ascii_paths_match_their_encoded_form():
	text = "User-agent: *\nDisallow: /café"
	assert not _allowed(text, "/caf%C3%A9/menu")


#--------------------
#	File syntax
#--------------------

def test_comments_and_spaces_are_ignored():
	text = "# hello\nUser-agent : * # everyone\n  Disallow :  /tmp/   # temporary"
	assert not _allowed(text, "/tmp/x")


def test_keys_are_case_insensitive():
	assert not _allowed("USER-AGENT: *\nDISALLOW: /x", "/x")


def test_utf8_bom_is_ignored():
	assert not _allowed("﻿User-agent: *\nDisallow: /x", "/x")


def test_rules_before_any_user_agent_are_ignored():
	assert _allowed("Disallow: /\nUser-agent: Googlebot\nDisallow: /", "/page")


def test_unknown_lines_are_ignored():
	text = "Sitemap: https://site.test/s.xml\nnonsense line\nUser-agent: *\nDisallow: /x"
	assert not _allowed(text, "/x")


#--------------------
#	Crawl-delay
#--------------------

def test_crawl_delay_of_our_group():
	assert _rules("User-agent: Arachnida\nCrawl-delay: 2.5").crawl_delay == 2.5


@pytest.mark.parametrize("value", ["abc", "-1", ""])
def test_invalid_crawl_delay_is_ignored(value: str):
	assert _rules(f"User-agent: *\nCrawl-delay: {value}").crawl_delay is None


#--------------------
#	Robustness
#--------------------

def test_hostile_pattern_does_not_hang():
	# With a backtracking regex this pattern takes exponential time.
	pattern = "/" + "*a" * 30 + "b"
	text = f"User-agent: *\nDisallow: {pattern}"
	start = time.monotonic()
	_allowed(text, "/" + "a" * 3000)
	assert time.monotonic() - start < 2


#--------------------
#	Cache and HTTP status
#--------------------

@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch) -> list[str]:
	"""
	Records robots.txt requests; answers depend on the host.
	"""
	calls: list[str] = []
	answers = {
		"https://ok.test/robots.txt": (200, b"User-agent: *\nDisallow: /no\nCrawl-delay: 3"),
		"https://missing.test/robots.txt": (404, b"Not found"),
		"https://forbidden.test/robots.txt": (403, b""),
		"https://broken.test/robots.txt": (503, b""),
	}

	def fake_fetch_robots(url: str) -> tuple[int, bytes] | None:
		calls.append(url)
		return answers.get(url)

	monkeypatch.setattr(robots, "fetch_robots", fake_fetch_robots)
	monkeypatch.setattr(fetcher, "_delays", {})
	return calls


def test_rules_are_applied(served: list[str]):
	cache = RobotsCache()
	assert cache.allows("https://ok.test/yes")
	assert not cache.allows("https://ok.test/no")


def test_robots_txt_fetched_once_per_origin(served: list[str]):
	cache = RobotsCache()
	for path in ("/a", "/b", "/no"):
		cache.allows("https://ok.test" + path)
	assert served == ["https://ok.test/robots.txt"]


@pytest.mark.parametrize("host", ["missing.test", "forbidden.test"])
def test_client_error_means_no_restriction(served: list[str], host: str):
	assert RobotsCache().allows(f"https://{host}/anything")


@pytest.mark.parametrize("host", ["broken.test", "unreachable.test"])
def test_server_error_or_unreachable_blocks_everything(served: list[str], host: str):
	assert not RobotsCache().allows(f"https://{host}/anything")


def test_crawl_delay_is_passed_to_the_fetcher(served: list[str]):
	RobotsCache().allows("https://ok.test/yes")
	assert fetcher._delays == {"https://ok.test": 3.0}