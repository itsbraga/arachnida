#!/usr/bin/env python3

import argparse
import sys

from spider.fetcher import fetch


def parse_args(argv: list[str]) -> argparse.Namespace:

	parser = argparse.ArgumentParser(
		prog="spider",
		description="Downloads images from a website recursively.",
	)

	parser.add_argument(
		"-r",
		action="store_true",
		help="recursively download images from the given URL",
	)
	parser.add_argument(
		"-l",
		type=int,
		default=5,
		metavar="N",
		help="maximum depth of recursion (default: 5); requires -r",
	)
	parser.add_argument(
		"-p",
		type=str,
		default="./data/",
		metavar="PATH",
		help="destination directory for downloaded images (default: ./data/)",
	)
	parser.add_argument(
		"url",
		type=str,
		help="starting URL to crawl",
	)

	return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:

	args = parse_args(argv if argv is not None else sys.argv[1:])

	print(f"[spider] fetching: {args.url}")

	html = fetch(args.url)
	if html is None:
		print("[spider] failed to fetch URL", file=sys.stderr)
		return 1

	print(f"[spider] got {len(html)} characters of HTML")
	print("[spider] first 300 chars:")
	print("-" * 60)
	print(html[:300])
	print("-" * 60)

	return 0


if __name__ == "__main__":
	sys.exit(main())
