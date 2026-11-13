#-----------------------------
#	Spider / Orchestration
#-----------------------------

import sys
from pathlib import Path

from spider.cli import parse_args
from spider.crawler import crawl
from common.colors import NC, BOLD, PINK, P_GREEN


def main(argv: list[str] | None = None) -> int:
	args = parse_args(argv if argv is not None else sys.argv[1:])

	dest_dir = Path(args.p)
	print(f"{BOLD}{PINK}[spider] START --- args: recursive={args.r}, max_depth={args.l}, "
	      f"dest={dest_dir}{NC}")

	saved = crawl(start_url=args.url, dest_dir=dest_dir, recursive=args.r, max_depth=args.l)
	print(f"{BOLD}{P_GREEN}[spider] DONE --- {saved} image(s) saved{NC}")

	return 0


if __name__ == "__main__":
	sys.exit(main())