#-----------------------------
#	Spider / Orchestration
#-----------------------------

import sys
import os
from pathlib import Path

from spider.cli import parse_args
from spider.crawler import crawl
from common.colors import NC, BOLD, P_PURPLE, P_GREEN, error


def main(argv: list[str] | None = None) -> int:
	args = parse_args(argv if argv is not None else sys.argv[1:])

	dest_dir = _prepare_dest_dir(args.p)
	if dest_dir is None:
		return 1

	print(f"{BOLD}{P_PURPLE}START  ---  args: recursive={args.r}, max_depth={args.l}, "
	      f"dest={dest_dir}{NC}")
	print("******\n")

	saved = crawl(start_url=args.URL, dest_dir=dest_dir, recursive=args.r, max_depth=args.l)
	print("\n*****")
	print(f"{BOLD}{P_GREEN}DONE  ---  {saved} image(s) saved{NC}")

	return 0


if __name__ == "__main__":
	sys.exit(main())


#--------------
#	PRIVATE
#--------------

def _prepare_dest_dir(raw_path: str) -> Path | None:
	"""
	Creates the destination directory if needed and checks it is writable.
	Returns None when it cannot be used.
	"""
	dest_dir = Path(raw_path)

	try:
		dest_dir.mkdir(parents=True, exist_ok=True)
	except OSError as e:
		error("spider", f"cannot use destination '{dest_dir}': {e}")
		return None

	if not os.access(dest_dir, os.W_OK | os.X_OK):
		error("spider", f"destination is not writable: {dest_dir}")
		return None

	return dest_dir