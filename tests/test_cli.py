#---------------------------------
#	Tests / CLI argument parsing
#---------------------------------

import pytest
from spider.cli import parse_args, DEFAULT_DEPTH


URL = "https://site.test/"


def test_defaults():
	args = parse_args([URL])
	assert (args.r, args.l, args.p, args.URL) == (False, DEFAULT_DEPTH, "./data/", URL)


def test_recursive_with_depth():
	args = parse_args(["-r", "-l", "2", "-p", "out", URL])
	assert (args.r, args.l, args.p) == (True, 2, "out")


def test_grouped_short_flags():
	args = parse_args(["-rl1", URL])
	assert (args.r, args.l) == (True, 1)


def test_depth_zero_is_allowed():
	assert parse_args(["-r", "-l", "0", URL]).l == 0


@pytest.mark.parametrize("argv", [
	["-r", "-l", "-3", URL],		# negative depth
	["-r", "-l", "abc", URL],		# not a number
	["-l", "2", URL],				# -l without -r
	["site.test"],					# no scheme
	["ftp://site.test/"],			# wrong scheme
	["https://"],					# no host
	[],								# no URL at all
])
def test_invalid_arguments_exit_with_code_2(argv, capsys):
	with pytest.raises(SystemExit) as exit_info:
		parse_args(argv)
	assert exit_info.value.code == 2