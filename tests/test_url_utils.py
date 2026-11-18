#------------------------------------------
#	Tests / URL manipulation utilities
#------------------------------------------

from spider.url_utils import normalize, is_in_scope


def test_normalize_lowercases_scheme_and_host():
	assert normalize("HTTPS://Example.COM/Page") == "https://example.com/Page"


def test_normalize_keeps_path_case():
	# Paths are case-sensitive on most servers: only the host is lowercased
	assert normalize("https://example.com/A/b") == "https://example.com/A/b"


def test_normalize_strips_fragment():
	assert normalize("https://example.com/page#section") == "https://example.com/page"


def test_normalize_keeps_query():
	assert normalize("https://example.com/p?id=3") == "https://example.com/p?id=3"


def test_normalize_empty_path_becomes_root():
	assert normalize("https://example.com") == normalize("https://example.com/")


def test_in_scope_same_origin():
	assert is_in_scope("https://example.com/a/b", "https://example.com/")


def test_out_of_scope_other_host():
	assert not is_in_scope("https://evil-corp.com/", "https://example.com/")


def test_out_of_scope_subdomain():
	assert not is_in_scope("https://blog.example.com/", "https://example.com/")


def test_out_of_scope_other_scheme():
	assert not is_in_scope("http://example.com/", "https://example.com/")


def test_out_of_scope_other_port():
	assert not is_in_scope("https://example.com:8443/", "https://example.com/")
