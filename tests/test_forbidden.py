"""Statické testy zakázaných konstrukcí v index.html (dod-3).

Používá jen standardní knihovnu. Soubor se čte až uvnitř testovacích funkcí.
Každý test nejprve ověří existenci index.html, aby nemohl projít vakuózně.
"""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"

FORBIDDEN_TOKENS = ("eval(", "new Function(", "Function(")
EXTERNAL_PREFIXES = ("http://", "https://", "//")


class _TagCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []  # (tag, {attr: value})

    def handle_starttag(self, tag, attrs):
        a = {}
        for name, value in attrs:
            key = (name or "").lower()
            if key not in a:
                a[key] = value if value is not None else ""
        self.tags.append((tag, a))


def _read_index():
    assert INDEX.is_file(), "index.html neexistuje v kořeni repozitáře: %s" % INDEX
    text = INDEX.read_text(encoding="utf-8")
    assert text.strip(), "index.html je prázdný"
    return text


def _tags():
    text = _read_index()
    p = _TagCollector()
    p.feed(text)
    p.close()
    return p.tags


def _is_external(value):
    v = (value or "").strip().lower()
    return any(v.startswith(prefix) for prefix in EXTERNAL_PREFIXES)


def test_index_exists():
    _read_index()


def test_no_eval_or_function_constructor():
    text = _read_index()
    found = [tok for tok in FORBIDDEN_TOKENS if tok in text]
    assert not found, "index.html obsahuje zakázané konstrukce: %r" % (found,)


def test_no_forbidden_tokens_ignoring_whitespace():
    # 'eval (' nebo 'new  Function (' nesmí obejít kontrolu
    text = _read_index()
    compact = "".join(text.split())
    found = [tok for tok in ("eval(", "newFunction(", "Function(") if tok in compact]
    assert not found, "index.html obsahuje zakázané konstrukce (po odstranění bílých znaků): %r" % (found,)


def test_no_external_src_or_href():
    tags = _tags()
    assert tags, "index.html neobsahuje žádné HTML značky"
    offenders = []
    for tag, attrs in tags:
        for key in ("src", "href"):
            if key in attrs and _is_external(attrs[key]):
                offenders.append((tag, key, attrs[key]))
    assert not offenders, "nalezeny externí odkazy: %r" % (offenders,)


def test_no_script_with_src():
    tags = _tags()
    scripts = [attrs for tag, attrs in tags if tag == "script"]
    assert scripts, "index.html neobsahuje žádný <script>"
    with_src = [attrs for attrs in scripts if "src" in attrs]
    assert not with_src, "<script> nesmí mít atribut src: %r" % (with_src,)


def test_no_stylesheet_link_with_href():
    tags = _tags()
    assert tags, "index.html neobsahuje žádné HTML značky"
    offenders = []
    for tag, attrs in tags:
        if tag != "link":
            continue
        rel = (attrs.get("rel") or "").lower().split()
        if "stylesheet" in rel and "href" in attrs:
            offenders.append(attrs)
    assert not offenders, "<link rel=\"stylesheet\"> s href je zakázán: %r" % (offenders,)
