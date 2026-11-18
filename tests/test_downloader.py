#---------------------------------------
#	Tests / Image downloading module
#---------------------------------------

import os
import pytest

import spider.downloader as downloader
from spider.downloader import fetch_image, save_image, _detect_format, _build_filename


JPEG = b"\xff\xd8\xff\xe0" + b"jpeg-body"
PNG = b"\x89PNG\r\n\x1a\n" + b"png-body"
GIF = b"GIF89a" + b"gif-body"
BMP = b"BM" + b"bmp-body"
HASH = "0123456789abcdef" * 4


#--------------------
#	Magic bytes
#--------------------

@pytest.mark.parametrize("content, fmt", [(JPEG, "jpg"), (PNG, "png"), (GIF, "gif"), (BMP, "bmp")])
def test_detect_format_known_images(content: bytes, fmt: str):
	assert _detect_format(content) == fmt


@pytest.mark.parametrize("content", [b"<!doctype html><html>", b"%PDF-1.7", b"MZ\x90\x00", b""])
def test_detect_format_rejects_non_images(content: bytes):
	assert _detect_format(content) is None


#--------------------
#	File names
#--------------------

def test_filename_uses_real_format_not_url_extension():
	# A PNG served under a .jpg URL is saved as .png
	assert _build_filename("https://a.test/logo.jpg", HASH, "png") == "01234567_logo.png"


def test_filename_strips_dangerous_characters():
	name = _build_filename("https://a.test/x/%2e%2e%2fevil%00name.jpg", HASH, "jpg")
	assert "/" not in name and "%" not in name and "\x00" not in name
	assert name.startswith("01234567_")


def test_filename_cannot_escape_destination():
	name = _build_filename("https://a.test/../../etc/passwd.jpg", HASH, "jpg")
	assert os.sep not in name
	assert not name.startswith(".")


def test_filename_falls_back_to_hash_without_basename():
	assert _build_filename("https://a.test/", HASH, "gif") == "01234567.gif"


def test_filename_length_is_capped():
	name = _build_filename("https://a.test/" + "a" * 500 + ".jpg", HASH, "jpg")
	assert len(name) <= len("01234567_") + 50 + len(".jpg")


#--------------------
#	fetch_image
#--------------------

def test_fetch_image_accepts_real_image(monkeypatch):
	monkeypatch.setattr(downloader, "http_get", lambda url, max_bytes: (PNG, url))
	assert fetch_image("https://a.test/p.png") == (PNG, "png")


def test_fetch_image_rejects_html_disguised_as_image(monkeypatch):
	monkeypatch.setattr(downloader, "http_get", lambda url, max_bytes: (b"<html>", url))
	assert fetch_image("https://a.test/fake.jpg") is None


def test_fetch_image_rejects_empty_body(monkeypatch):
	monkeypatch.setattr(downloader, "http_get", lambda url, max_bytes: (b"", url))
	assert fetch_image("https://a.test/empty.jpg") is None


def test_fetch_image_propagates_network_failure(monkeypatch):
	monkeypatch.setattr(downloader, "http_get", lambda url, max_bytes: None)
	assert fetch_image("https://a.test/down.jpg") is None


#--------------------
#	save_image
#--------------------

def test_save_image_writes_file_and_leaves_no_part(tmp_path):
	saved = save_image(JPEG, "jpg", "https://a.test/cat.jpg", tmp_path)
	assert saved is not None and saved.read_bytes() == JPEG
	assert list(tmp_path.glob("*.part")) == []


def test_save_image_write_failure_returns_none(tmp_path):
	missing_dir = tmp_path / "does-not-exist"
	assert save_image(JPEG, "jpg", "https://a.test/cat.jpg", missing_dir) is None
