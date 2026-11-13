#------------------------------------
#	Spider / CLI argument parsing
#------------------------------------

import argparse
from urllib.parse import urlparse


DEFAULT_DEPTH = 5


#--------------
#	PUBLIC
#--------------

def parse_args(argv: list[str]) -> argparse.Namespace:
	"""
	Parses command-line arguments

	Expecting: ./spider [-rlp] URL

	• -r		: Recursively downloads the images in a URL received as a parameter.
	• -r -l [N]	: Indicates the maximum depth level of the recursive download.
				  If not indicated, it will be 5.
	• -p [PATH]	: Indicates the path where the downloaded files will be saved.
				  If not specified, ./data/ will be used.
	"""
	parser = argparse.ArgumentParser(
		prog="spider",
		description="Downloads images from a website recursively.")
	parser.add_argument("-r", action="store_true",
						help="recursively download images from the given URL")
	parser.add_argument("-l", type=_depth, default=None, metavar="DEPTH",
						help="maximum depth of recursion (default: 5); requires -r")
	parser.add_argument("-p", type=str, default="./data/", metavar="PATH",
						help="destination directory for downloaded images (default: ./data/)")
	parser.add_argument("URL", type=_http_url,
						help="starting URL to crawl")

	args = parser.parse_args(argv)

	if args.l is not None and not args.r:
		parser.error("-l requires -r")
	if args.l is None:
		args.l = DEFAULT_DEPTH

	return args


#--------------
#	PRIVATE
#--------------

def _depth(value: str) -> int:
	"""
	Converts the -l value to a non-negative integer.
	"""
	try:
		depth = int(value)
	except ValueError:
		raise argparse.ArgumentTypeError(f"invalid depth: '{value}'")

	if depth < 0:
		raise argparse.ArgumentTypeError(f"depth must be >= 0, got {depth}")

	return depth

def _http_url(value: str) -> str:
	"""
	Accepts only absolute http(s) URLs.
	"""
	parsed = urlparse(value)
	if parsed.scheme not in ("http", "https") or not parsed.netloc:
		raise argparse.ArgumentTypeError(
			f"invalid URL: '{value}' (expected http:// or https://)")

	return value