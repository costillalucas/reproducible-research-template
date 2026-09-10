"""Negative control for the gate itself.

The rest of the suite shows check_provenance.py passing on a correct
report. That alone would not prove much -- a checker that always exits 0
would pass it too. This test corrupts a real, tag-carrying copy of
report/report.md (one literal changed so it disagrees with the registry)
and asserts the gate is caught refusing it.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


def _run_gate(deliverable_path):
    return subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "check_provenance.py"), deliverable_path],
        capture_output=True, text=True,
    )


def test_gate_passes_on_the_real_report():
    result = _run_gate(os.path.join(ROOT, "report", "report.md"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "all checks pass" in result.stdout


def test_gate_rejects_a_wrong_literal(tmp_path):
    with open(os.path.join(ROOT, "report", "report.md")) as fh:
        text = fh.read()
    # pi cannot be 4.0 -- change the displayed pi_true literal and nothing else.
    broken, n = re.subn(r"\[srcnum:pi_true:[^\]]+\]", "[srcnum:pi_true:4.00000]", text)
    assert n == 1, "fixture assumption broke: pi_true tag not found as expected"
    broken_report = tmp_path / "report.md"
    broken_report.write_text(broken)

    result = _run_gate(str(broken_report))
    assert result.returncode == 1
    assert "pi_true" in result.stdout
    assert "does not match" in result.stdout


def test_gate_rejects_a_reference_to_an_unknown_key(tmp_path):
    with open(os.path.join(ROOT, "report", "report.md")) as fh:
        text = fh.read()
    broken = text + "\n\nAnd one more thing [src:this_key_does_not_exist].\n"
    broken_report = tmp_path / "report.md"
    broken_report.write_text(broken)

    result = _run_gate(str(broken_report))
    assert result.returncode == 1
    assert "this_key_does_not_exist" in result.stdout
