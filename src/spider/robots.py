#--------------------------------------------------------------------------------
#	Spider / robots.txt: parsing and matching per RFC 9309, cached per origin
#--------------------------------------------------------------------------------

from dataclasses import dataclass, field
from urllib.parse import quote, urlsplit

from spider.fetcher import AGENT_TOKEN, fetch_robots, set_crawl_delay
from spider.url_utils import origin
from common.colors import warn


# Characters kept as-is when percent-encoding paths and patterns:
# '%' so existing escapes are not encoded twice, '*' and '$' for wildcards
_SAFE_CHARS = "/:@!$&'()*+,;=?%"


@dataclass(frozen=True)
class _Rule:
	allow: bool
	pattern: str


@dataclass
class _Group:
	agents: list[str] = field(default_factory=list)
	rules: list[_Rule] = field(default_factory=list)
	crawl_delay: float | None = None


@dataclass(frozen=True)
class RobotRules:
	"""
	The rules of one robots.txt that apply to our crawler.
	"""
	rules: tuple[_Rule, ...] = ()
	crawl_delay: float | None = None
	disallow_all: bool = False

	def allows(self, url: str) -> bool:
		"""
		The longest matching rule wins; on equal length, Allow wins.
		No matching rule means allowed.
		"""
		if self.disallow_all:
			return False
		target = _target(url)
		if target == "/robots.txt":
			return True

		best: tuple[int, bool] | None = None
		for rule in self.rules:
			if _match(rule.pattern, target):
				candidate = (len(rule.pattern), rule.allow)		# True > False: Allow wins ties
				if best is None or candidate > best:
					best = candidate

		return best is None or best[1]


#--------------
#	PUBLIC
#--------------

def parse_robots(text: str, agent: str) -> RobotRules:
	"""
	Keeps only the rules of the groups that apply to agent: the groups
	naming it if any, else the '*' groups. Groups for the same agent merge.
	"""
	groups = _parse_groups(text.lstrip("﻿"))
	token = agent.lower()

	selected = [g for g in groups if token in g.agents]
	if not selected:
		selected = [g for g in groups if "*" in g.agents]

	rules = tuple(rule for g in selected for rule in g.rules)
	delays = [g.crawl_delay for g in selected if g.crawl_delay is not None]

	return RobotRules(rules, max(delays) if delays else None)


class RobotsCache:
	"""
	Fetches each origin's robots.txt once, on first use.
	"""

	def __init__(self) -> None:
		self._rules: dict[str, RobotRules] = {}


	def allows(self, url: str) -> bool:
		"""
		True if our crawler may fetch url according to its origin's robots.txt.
		"""
		key = origin(url)
		if key not in self._rules:
			self._rules[key] = self._load(key)

		return self._rules[key].allows(url)


	def _load(self, key: str) -> RobotRules:
		"""
		RFC 9309: 4xx means no robots.txt (everything allowed);
		5xx or an unreachable server means everything disallowed.
		"""
		result = fetch_robots(key + "/robots.txt")
		if result is None:
			warn("robots", f"robots.txt unreachable, nothing crawled on {key}")
			return RobotRules(disallow_all=True)

		status, body = result
		if 400 <= status < 500:
			return RobotRules()
		if not 200 <= status < 300:
			warn("robots", f"robots.txt answered HTTP {status}, nothing crawled on {key}")
			return RobotRules(disallow_all=True)

		rules = parse_robots(body.decode("utf-8", errors="replace"), AGENT_TOKEN)
		if rules.crawl_delay is not None:
			set_crawl_delay(key, rules.crawl_delay)

		return rules


#--------------
#	PRIVATE
#--------------

def _parse_groups(text: str) -> list[_Group]:
	"""
	A group is one or more user-agent lines followed by rules.
	A user-agent line after a rule starts a new group.
	"""
	groups: list[_Group] = []
	current: _Group | None = None
	in_rules = False

	for line in text.splitlines():
		key, value = _split_line(line)
		if key == "user-agent":
			if current is None or in_rules:
				current = _Group()
				groups.append(current)
				in_rules = False
			current.agents.append(_product_token(value))
		elif current is not None and key in ("allow", "disallow", "crawl-delay"):
			in_rules = True
			_add_record(current, key, value)

	return groups


def _add_record(group: _Group, key: str, value: str) -> None:
	"""
	An empty Allow or Disallow is not a rule: "Disallow:" allows everything.
	"""
	if key == "crawl-delay":
		group.crawl_delay = _parse_delay(value)
	elif value:
		group.rules.append(_Rule(key == "allow", _encode(value)))


def _split_line(line: str) -> tuple[str, str]:
	"""
	"Key: value # comment" -> ("key", "value"). Keys are case-insensitive.
	"""
	line = line.split("#", 1)[0]
	key, sep, value = line.partition(":")
	if not sep:
		return "", ""
	return key.strip().lower(), value.strip()


def _product_token(value: str) -> str:
	"""
	"Arachnida/1.0" -> "arachnida". Agent names match case-insensitively.
	"""
	return value.split("/", 1)[0].strip().lower()


def _parse_delay(value: str) -> float | None:
	try:
		delay = float(value)
	except ValueError:
		return None
	return delay if delay >= 0 else None


def _target(url: str) -> str:
	"""
	The part of the URL rules apply to: path and query, percent-encoded.
	"""
	parts = urlsplit(url)
	target = parts.path or "/"
	if parts.query:
		target += "?" + parts.query
	return _encode(target)


def _encode(text: str) -> str:
	"""
	Percent-encodes non-ASCII characters so "/café" and "/caf%C3%A9" compare equal.
	"""
	return quote(text, safe=_SAFE_CHARS)


def _match(pattern: str, target: str) -> bool:
	"""
	Prefix match with '*' wildcards and an optional final '$' anchor.
	Iterative with a single backtrack point: at worst proportional to
	len(pattern) * len(target), never exponential. No regex on purpose:
	a hostile robots.txt must not be able to trigger a ReDoS.
	"""
	if pattern.endswith("$"):
		pattern = pattern[:-1]
	else:
		pattern += "*"	# a prefix match is the pattern followed by anything

	p = t = 0
	star, mark = -1, 0

	while t < len(target):
		if p < len(pattern) and pattern[p] == "*":
			star, mark = p, t
			p += 1
		elif p < len(pattern) and pattern[p] == target[t]:
			p += 1
			t += 1
		elif star != -1:
			p, mark = star + 1, mark + 1
			t = mark
		else:
			return False

	return pattern[p:].strip("*") == ""