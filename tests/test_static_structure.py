"""Statické testy kostry index.html (dod-1).

Používá jen standardní knihovnu. Soubor se čte až uvnitř testovacích funkcí,
aby chybějící index.html vedl k selhání testu (exit 1), ne k chybě sběru.
"""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"


class _Collector(HTMLParser):
    """Sbírá deklarace, atributy a texty, které testy potřebují."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.decls = []
        self.html_tags = []  # seznam dict atributů každého <html>
        self.metas = []  # seznam dict atributů každého <meta>
        self.scripts = []  # seznam dict atributů každého <script>
        self.h1_texts = []
        self._h1_depth = 0
        self._h1_buf = []

    @staticmethod
    def _attrs(attrs):
        out = {}
        for name, value in attrs:
            key = (name or "").lower()
            if key not in out:
                out[key] = value if value is not None else ""
        return out

    def handle_decl(self, decl):
        self.decls.append(decl)

    def handle_starttag(self, tag, attrs):
        a = self._attrs(attrs)
        if tag == "html":
            self.html_tags.append(a)
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "script":
            self.scripts.append(a)
        elif tag == "h1":
            self._h1_depth += 1
            if self._h1_depth == 1:
                self._h1_buf = []

    def handle_endtag(self, tag):
        if tag == "h1" and self._h1_depth > 0:
            self._h1_depth -= 1
            if self._h1_depth == 0:
                self.h1_texts.append("".join(self._h1_buf))
                self._h1_buf = []

    def handle_data(self, data):
        if self._h1_depth > 0:
            self._h1_buf.append(data)


def _read_index():
    assert INDEX.is_file(), "index.html neexistuje v kořeni repozitáře: %s" % INDEX
    text = INDEX.read_text(encoding="utf-8")
    assert text.strip(), "index.html je prázdný"
    return text


def _parse():
    text = _read_index()
    parser = _Collector()
    parser.feed(text)
    parser.close()
    return text, parser


def test_index_exists_and_not_empty():
    _read_index()


def test_doctype_html():
    _, p = _parse()
    normalized = [" ".join(d.strip().lower().split()) for d in p.decls]
    assert "doctype html" in normalized, "chybí <!DOCTYPE html>, nalezeno: %r" % (p.decls,)


def test_doctype_is_first_thing_in_file():
    text, _ = _parse()
    head = text.lstrip("\ufeff \t\r\n").lower()
    assert head.startswith("<!doctype html"), "<!DOCTYPE html> musí být na úplném začátku souboru"


def test_html_lang_cs():
    _, p = _parse()
    assert len(p.html_tags) == 1, "očekáván právě jeden <html>, nalezeno %d" % len(p.html_tags)
    lang = (p.html_tags[0].get("lang") or "").strip().lower()
    assert lang == "cs", "<html lang> musí být 'cs', je %r" % lang


def test_meta_charset_utf8():
    _, p = _parse()
    charsets = [(m.get("charset") or "").strip().lower() for m in p.metas if "charset" in m]
    assert "utf-8" in charsets, "chybí <meta charset=\"utf-8\">, nalezeno: %r" % (charsets,)


def test_meta_viewport_width_device_width():
    _, p = _parse()
    viewports = [m for m in p.metas if (m.get("name") or "").strip().lower() == "viewport"]
    assert viewports, "chybí <meta name=\"viewport\">"
    contents = ["".join((m.get("content") or "").lower().split()) for m in viewports]
    assert any("width=device-width" in c for c in contents), (
        "content viewportu musí obsahovat width=device-width, nalezeno: %r" % (contents,)
    )


def test_h1_contains_kalkulacka():
    _, p = _parse()
    assert p.h1_texts, "v dokumentu chybí <h1>"
    joined = [" ".join(t.split()) for t in p.h1_texts]
    assert any("Kalkulačka" in t for t in joined), "žádný <h1> neobsahuje text 'Kalkulačka': %r" % (joined,)


def test_exactly_one_script_calc_core():
    _, p = _parse()
    core = [s for s in p.scripts if (s.get("id") or "").strip() == "calc-core"]
    assert len(core) == 1, "očekáván právě jeden <script id=\"calc-core\">, nalezeno %d" % len(core)
