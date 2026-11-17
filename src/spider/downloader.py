#---------------------------------------------------------------------------------
#	Spider / Image downloading module: Download an image, review it, and save it.
#---------------------------------------------------------------------------------

from pathlib import Path
from urllib.parse import urlparse
import hashlib

from spider.fetcher import http_get
from common.colors import warn, error


"""
Each file format begins with a distinctive sequence of byte (the "magic number")
that uniquely identifies it. This is reliable, unlike the file extension.

	Format	|	Magic bytes (hexadecimal)
	-------------------------------------
	JPEG	|	FF D8 FF
	PNG		|	89 50 4E 47 0D 0A 1A 0A
	GIF		|	47 49 46 38 (GIF8)
	BMP		|	42 4D (BM)
"""
MAGIC_BYTES: dict[str, bytes] = {
    "jpg":  b"\xff\xd8\xff",
    "png":  b"\x89PNG\r\n\x1a\n",
    "gif":  b"GIF8",
    "bmp":  b"BM",
}

MAX_IMAGE_BYTES = 20 * 1024 * 1024		# 20 MB safety cap


#--------------
#	PUBLIC
#--------------

def fetch_image(url: str) -> tuple[bytes, str] | None:
	"""
	Downloads one image and checks its magic bytes.
	Returns (content, fmt) on success, None on any error or rejection.
	"""
	result = http_get(url, MAX_IMAGE_BYTES)
	if result is None:
		return None

	content, _ = result
	if not content:
		warn("downloader", f"empty response: {url}")
		return None

	fmt = _detect_format(content)
	if fmt is None:
		warn("downloader", f"not a recognised image: {url}")
		return None

	return content, fmt


def save_image(content: bytes, fmt: str, url: str, dest_dir: Path) -> Path | None:
	"""
	Writes the image atomically under a collision-free name.
	Returns the saved Path, or None if the write failed.
	"""
	content_hash = hashlib.sha256(content).hexdigest()

	dest_path = dest_dir / _build_filename(url, content_hash, fmt)
	tmp_path = dest_path.with_name(dest_path.name + ".part")

	try:
		tmp_path.write_bytes(content)
		tmp_path.replace(dest_path)
	except OSError as e:
		tmp_path.unlink(missing_ok=True)
		error("downloader", f"write failed: {dest_path} - {e}")
		return None
	except KeyboardInterrupt:
		tmp_path.unlink(missing_ok=True)
		raise

	return dest_path


#--------------
#	PRIVATE
#--------------

def _detect_format(content: bytes) -> str | None:
	"""
	Returns the format key ('jpg', 'png', ...) or None if unknown.
	"""
	for fmt, magic in MAGIC_BYTES.items():
		if content.startswith(magic):
			return fmt

	return None


def _build_filename(url: str, content_hash: str, fmt: str) -> str:
	"""
	Builds a safe filename: <hash8>_<basename>.<ext>
	Falls back to <hash8>.<ext> if the URL has no usable basename.
	"""
	short_hash = content_hash[:8]
	path = urlparse(url).path
	basename = Path(path).name

	safe_base = "".join(c for c in basename if c.isalnum() or c in "._-")
	if not safe_base or "." not in safe_base:
		return f"{short_hash}.{fmt}"

	stem = Path(safe_base).stem[:50]

	return f"{short_hash}_{stem}.{fmt}"