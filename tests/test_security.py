#----------------------------------------------------------------------
#	Tests / Security invariants of the codebase
#
#	CVE-2026-126190, CVE-2026-126191 and CVE-2026-126193 (soupsieve)
#	were only reachable through CSS selectors. They are fixed by the
#	upgrade to soupsieve 4.1.3; this test is defence in depth: the
#	code must keep using find() / find_all() only.
#----------------------------------------------------------------------

from pathlib import Path
import pytest


SRC = Path(__file__).resolve().parent.parent / "src"
FORBIDDEN = (".select(", ".select_one(", ".css.")


@pytest.mark.parametrize("source", sorted(SRC.rglob("*.py")), ids=lambda p: p.name)
def test_no_css_selector(source: Path):
	text = source.read_text(encoding="utf-8")
	for pattern in FORBIDDEN:
		assert pattern not in text, f"{pattern} used in {source.name}: see README Security"