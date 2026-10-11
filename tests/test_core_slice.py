"""Testy jádra kalkulačky přes JS harness (dod-2).

Používá jen standardní knihovnu. index.html se čte (resp. harness se volá)
až uvnitř testovacích funkcí, aby chybějící index.html vedl k selhání testu
(exit 1), ne k chybě sběru (exit 2). Každý test nejprve ověří existenci
index.html, aby nemohl projít vakuózně.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
HARNESS = ROOT / "tests" / "harness.js"


def _assert_index_exists():
    assert INDEX.is_file(), "index.html neexistuje v kořeni repozitáře: %s" % INDEX
    assert HARNESS.is_file(), "chybí harness: %s" % HARNESS


def run(*keys):
    """Spustí harness s danými klávesami a vrátí dekódovaný JSON view."""
    _assert_index_exists()
    cmd = ["node", str(HARNESS), str(INDEX), *keys]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, (
        "harness selhal (exit %d) pro klávesy %r\nstderr:\n%s\nstdout:\n%s"
        % (proc.returncode, list(keys), proc.stderr, proc.stdout)
    )
    stdout = proc.stdout.strip()
    assert stdout, "harness nevypsal na stdout žádný JSON; stderr:\n%s" % proc.stderr
    try:
        return json.loads(stdout)
    except ValueError as e:
        raise AssertionError("stdout harnessu není platný JSON: %r (%s)" % (stdout, e))


def test_initial_state_display_zero_and_empty_expression():
    _assert_index_exists()
    view = run()
    assert isinstance(view, dict), "view musí být objekt, je %r" % (view,)
    assert view == {"display": "0", "expression": ""}, "výchozí view: %r" % (view,)


def test_vertical_slice_12_plus_8_equals_20():
    _assert_index_exists()
    view = run("1", "2", "+", "8", "=")
    assert isinstance(view, dict), "view musí být objekt, je %r" % (view,)
    assert "display" in view and "expression" in view, "view musí mít klíče display a expression: %r" % (view,)
    assert isinstance(view["display"], str), "display musí být řetězec, je %r" % (view["display"],)
    assert view["display"] == "20", "1,2,+,8,= musí dát display '20', dalo %r" % (view,)


def test_3_plus_4_equals_7():
    _assert_index_exists()
    view = run("3", "+", "4", "=")
    assert isinstance(view, dict), "view musí být objekt, je %r" % (view,)
    assert isinstance(view.get("display"), str), "display musí být řetězec: %r" % (view,)
    assert view["display"] == "7", "3,+,4,= musí dát display '7', dalo %r" % (view,)
