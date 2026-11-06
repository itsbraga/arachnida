"""
Spider / orchestration 
"""

import sys

from spider.cli import parse_args
from spider.fetcher import fetch
from spider.parser import extract_image_urls


def main(argv: list[str] | None = None) -> int:
	"""
	Entry point. Returns exit code (0 = success, non-zero = failure).
	"""
	args = parse_args(argv if argv is not None else sys.argv[1:])

	print(f"[spider] fetching: {args.url}")
	html = fetch(args.url)
	if html is None:
		print("[spider] failed to fetch URL", file=sys.stderr)
		return 1

	image_urls = extract_image_urls(html, args.url)

	print(f"[spider] found {len(image_urls)} image(s) on {args.url}")
	for url in sorted(image_urls):
		print(f" {url}")

	return 0


if __name__ == "__main__":
	sys.exit(main())