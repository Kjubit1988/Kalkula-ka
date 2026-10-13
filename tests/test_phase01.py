import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
HTML_PATH = ROOT_DIR / "index.html"
DOM_STUB_PATH = Path(__file__).resolve().parent / "_dom_stub.js"


class HTMLDOMTreeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root_nodes = []
        self.stack = []
        self.scripts = []
        self._current_script = []
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        node = {"tag": tag, "attributes": attrs_dict, "text": "", "children": []}
        if tag.lower() == "script":
            self._in_script = True
            self._current_script = []
        if self.stack:
            self.stack[-1]["children"].append(node)
        else:
            self.root_nodes.append(node)
        self.stack.append(node)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1]["tag"] == tag:
            node = self.stack.pop()
            if tag.lower() == "script":
                self._in_script = False
                self.scripts.append("".join(self._current_script))
                self._current_script = []

    def handle_data(self, data):
        if self._in_script:
            self._current_script.append(data)
        elif self.stack:
            self.stack[-1]["text"] += data


class ButtonDisplayCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.buttons = []
        self.display_text = None
        self._current_tag = None
        self._current_attrs = {}
        self._buffer = []

    def handle_starttag(self, tag, attrs):
        self._current_tag = tag
        self._current_attrs = dict(attrs)
        self._buffer = []

    def handle_endtag(self, tag):
        text = "".join(self._buffer).strip()
        if tag == "button":
            self.buttons.append({"type": self._current_attrs.get("type"), "text": text})
        if self._current_attrs.get("id") == "display":
            self.display_text = text
        self._current_tag = None
        self._current_attrs = {}
        self._buffer = []

    def handle_data(self, data):
        if self._current_tag is not None:
            self._buffer.append(data)


def test_html_structure_and_constraints():
    assert HTML_PATH.is_file(), f"Soubor {HTML_PATH} neexistuje."
    content = HTML_PATH.read_text(encoding="utf-8")

    assert re.search(r"<html[^>]*\blang=['\"]cs['\"]", content, re.IGNORECASE), (
        "Chybí <html lang=\"cs\">"
    )
    assert re.search(r"<meta[^>]*charset=['\"]?utf-8['\"]?", content, re.IGNORECASE), (
        "Chybí meta charset UTF-8"
    )
    assert re.search(r"<meta[^>]*name=['\"]viewport['\"]", content, re.IGNORECASE), (
        "Chybí <meta name=\"viewport\">"
    )
    assert re.search(r"<style[\s>].*?</style>", content, re.DOTALL | re.IGNORECASE), (
        "Chybí inline <style>...</style>"
    )
    assert re.search(r"<script[\s>].*?</script>", content, re.DOTALL | re.IGNORECASE), (
        "Chybí inline <script>...</script>"
    )

    assert not re.search(r"<script[^>]+src=", content, re.IGNORECASE), (
        "Zakázán externí <script src>"
    )
    assert not re.search(
        r"<link[^>]+rel=['\"]?stylesheet['\"]?", content, re.IGNORECASE
    ), "Zakázán externí <link rel=stylesheet>"
    assert "@import" not in content, "Zakázáno použití @import v CSS"
    assert not re.search(r"(?:src|href)\s*=\s*['\"]https?://", content, re.IGNORECASE), (
        "Zakázány vzdálené adresy v src nebo href"
    )

    forbidden_tokens = ["eval(", "Function(", "innerHTML"]
    for token in forbidden_tokens:
        assert token not in content, f"Zakázaný řetězec '{token}' nalezen v index.html"


def test_buttons_and_initial_display():
    assert HTML_PATH.is_file(), f"Soubor {HTML_PATH} neexistuje."
    content = HTML_PATH.read_text(encoding="utf-8")

    collector = ButtonDisplayCollector()
    collector.feed(content)

    required_labels = [
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
        "+", "\u2212", "\u00D7", "\u00F7", "=", ",", "AC", "\u00B1", "\u232B",
    ]

    for label in required_labels:
        matching = [
            b for b in collector.buttons
            if b["text"] == label and b["type"] == "button"
        ]
        assert matching, (
            f"Nenalezeno tlačítko s type='button' a ořezaným textem '{label}'"
        )

    assert collector.display_text == "0", (
        f"Element s id='display' má mít výchozí text '0', ale má '{collector.display_text}'"
    )


def test_vertical_slice_addition_and_ac(tmp_path):
    assert HTML_PATH.is_file(), f"Soubor {HTML_PATH} neexistuje."
    node_bin = shutil.which("node")
    assert node_bin is not None, "Příkaz node nebyl nalezen v PATH."

    content = HTML_PATH.read_text(encoding="utf-8")
    parser = HTMLDOMTreeParser()
    parser.feed(content)

    inline_script = "\n".join(parser.scripts)
    dom_stub = DOM_STUB_PATH.read_text(encoding="utf-8")
    tree_json = json.dumps(parser.root_nodes)

    runner_script = f"""{dom_stub}

const __tree = {tree_json};
for (const node of __tree) {{
  __buildDOM(node);
}}

{inline_script}

const domLoadedEvent = {{ type: 'DOMContentLoaded', target: document, currentTarget: document }};
document.dispatchEvent(domLoadedEvent);
window.dispatchEvent(domLoadedEvent);

__clickByText('8');
__clickByText('+');
__clickByText('5');
__clickByText('=');

const disp = document.getElementById('display');
if (!disp) {{
  throw new Error('Element #display nenalezen');
}}
console.log(disp.textContent.trim());

__clickByText('AC');
console.log(disp.textContent.trim());
"""

    test_runner_file = tmp_path / "run_calc.js"
    test_runner_file.write_text(runner_script, encoding="utf-8")

    res = subprocess.run(
        [node_bin, str(test_runner_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, (
        f"Node skript selhal s kódem {res.returncode}:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"
    )
    lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
    assert lines == ["13", "0"], f"Očekáván výstup ['13', '0'], obdrženo: {lines}"
