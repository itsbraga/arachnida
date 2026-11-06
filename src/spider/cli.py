"""
Spider / CLI argument parsing
"""

import argparse
import sys

from spider.fetcher import fetch
from spider.parser import extract_image_urls


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
	parser.add_argument("-l", type=int, default=5, metavar="DEPTH",
						help="maximum depth of recursion (default: 5); requires -r")
	parser.add_argument("-p", type=str, default="./data/", metavar="PATH",
						help="destination directory for downloaded images (default: ./data/)")
	parser.add_argument("url", type=str,
						help="starting URL to crawl")

	return parser.parse_args(argv)
