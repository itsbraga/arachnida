#---------------------------------------------------------------------------------
#	Spider / Image downloading module: Download an image, review it, and save it.
#---------------------------------------------------------------------------------

from pathlib import Path
from urllib.parse import urlparse
import requests
import hashlib
import urllib3

from spider.fetcher import USER_AGENT, DEFAULT_TIMEOUT
from common.colors import warn, error


"""
Each file format begins with a distinctive sequence of byte (the “magic number”)
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

def download_image(url: str, dest_dir: Path, seen_hashes: set[str]) -> Path | None:
	"""
	Downloads one image, validates its magic bytes, deduplicates by
	content hash, and saves it to dest_dir.
	Returns the saved Path on success, None on any rejection/error.
	"""
	headers = {"User-Agent": USER_AGENT}

	# 1. Fetch the raw bytes, with a size cap to avoid memory bombs
	try:
		with requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT, stream=True) as response:
			response.raise_for_status()
			content = response.raw.read(MAX_IMAGE_BYTES + 1, decode_content=True)
	except requests.exceptions.RequestException as e:
		error("downloader", f"fetch failed: {url} - {e}")
		return None
	except (urllib3.exceptions.HTTPError, OSError) as e:
		error("downloader", f"read failed: {url} - {e}")
		return None

	if len(content) > MAX_IMAGE_BYTES:
		warn("downloader", f"file too large (>{MAX_IMAGE_BYTES} bytes): {url}")
		return None
	if not content:
		warn("downloader", f"empty response: {url}")
		return None

	# 3. Validate real format via magic bytes
	real_format = _detect_format(content)
	if real_format is None:
		warn("downloader", f"not a recognised image: {url}")
		return None

	# 4. Deduplicate by content hash
	content_hash = hashlib.sha256(content).hexdigest()
	if content_hash in seen_hashes:
		warn("downloader", f"duplicate content skipped: {url}")
		return None
	seen_hashes.add(content_hash)

	# 5. Build a safe, collision-free filename
	filename = _build_filename(url, content_hash, real_format)
	dest_path = dest_dir / filename

	# 6. Write
	try:
		dest_path.write_bytes(content)
	except OSError as e:
		error("downloader", f"write failed: {dest_path} - {e}")
		return None

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