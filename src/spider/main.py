"""
Spider / orchestration 
"""

import sys
from pathlib import Path

from spider.cli import parse_args
from spider.fetcher import fetch
from spider.parser import extract_image_urls
from spider.downloader import download_image


def main(argv: list[str] | None = None) -> int:
	args = parse_args(argv if argv is not None else sys.argv[1:])

	print(f"[spider] fetching: {args.url}")
	html = fetch(args.url)
	if html is None:
		print("[spider] failed to fetch URL", file=sys.stderr)
		return 1

	image_urls = extract_image_urls(html, args.url)
	print(f"[spider] found {len(image_urls)} image candidate(s) on {args.url}")
	if not image_urls:
		return 0

	dest_dir = Path(args.p)
	seen_hashes: set[str] = set()
	saved_count = 0

	for url in sorted(image_urls):
		saved = download_image(url, dest_dir, seen_hashes)
		if saved:
				saved_count += 1
				print(f"[spider] saved: {saved}")

	print(f"[spider] All done! {saved_count}/{len(image_urls)} images saved to {dest_dir}/", file=sys.stderr)

	return 0


if __name__ == "__main__":
	sys.exit(main())