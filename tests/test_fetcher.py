#--------------------------------------------------------
#	Tests / Fetcher module (no real network: fake session)
#--------------------------------------------------------

from types import SimpleNamespace
import pytest
import requests

import spider.fetcher as fetcher


class FakeResponse:
	"""
	Minimal stand-in for requests.Response, usable with `with`.
	"""

	def __init__(self, body: bytes = b"<html></html>", content_type: str = "text/html",
				status: int = 200, url: str = "https://site.test/"):
		self.status_code = status
		self.headers = {"Content-Type": content_type}
		self.url = url
		self.raw = SimpleNamespace(read=lambda n, decode_content=True: body[:n])

	def __enter__(self):
		return self

	def __exit__(self, *exc):
		return False

	def raise_for_status(self):
		if self.status_code >= 400:
			raise requests.exceptions.HTTPError(response=self)


#--------------
#	PUBLIC
#--------------

@pytest.fixture(autouse=True)
def no_delay(monkeypatch):
	monkeypatch.setattr(fetcher, "REQUEST_DELAY", 0)


def test_fetch_returns_html_and_final_url(monkeypatch):
	_serve(monkeypatch, FakeResponse(b"<p>hi</p>", url="https://site.test/moved/"))
	assert fetcher.fetch("https://site.test/") == (b"<p>hi</p>", "https://site.test/moved/")


def test_fetch_rejects_non_html(monkeypatch):
	_serve(monkeypatch, FakeResponse(b"\x89PNG", content_type="image/png"))
	assert fetcher.fetch("https://site.test/a.png") is None


def test_http_get_accepts_non_html_when_not_required(monkeypatch):
	_serve(monkeypatch, FakeResponse(b"\x89PNG", content_type="image/png"))
	assert fetcher.http_get("https://site.test/a.png", 100) == (b"\x89PNG", "https://site.test/")


def test_http_get_enforces_size_cap(monkeypatch):
	_serve(monkeypatch, FakeResponse(b"x" * 101))
	assert fetcher.http_get("https://site.test/", 100) is None


def test_http_get_accepts_exact_size_cap(monkeypatch):
	_serve(monkeypatch, FakeResponse(b"x" * 100))
	assert fetcher.http_get("https://site.test/", 100) is not None


def test_http_error_returns_none(monkeypatch):
	_serve(monkeypatch, FakeResponse(status=404))
	assert fetcher.fetch("https://site.test/missing") is None


@pytest.mark.parametrize("exc", [
	requests.exceptions.Timeout(),
	requests.exceptions.ConnectionError(),
	requests.exceptions.TooManyRedirects(),
	OSError("connection reset"),
])
def test_network_failures_return_none(monkeypatch, exc):
	_serve(monkeypatch, exc=exc)
	assert fetcher.fetch("https://site.test/") is None


#--------------
#	PRIVATE
#--------------

def _serve(monkeypatch, response=None, exc=None):
	def fake_get(url, **kwargs):
		if exc is not None:
			raise exc
		return response
	monkeypatch.setattr(fetcher._session, "get", fake_get)