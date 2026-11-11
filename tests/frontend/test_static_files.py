"""Pruebas del frontend: enlaces, recursos y sintaxis JavaScript."""

import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
FRONTENDS = [ROOT / "app" / "frontend", ROOT / "app" / "stage-2" / "frontend"]
HTML_FILES = sorted(path for folder in FRONTENDS for path in folder.glob("*.html"))
JS_FILES = sorted(path for folder in FRONTENDS for path in folder.glob("*.js"))


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.references = []
        self.lang = None
        self.has_title = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "html":
            self.lang = attributes.get("lang")
        if tag == "title":
            self.has_title = True
        if "id" in attributes:
            self.ids.add(attributes["id"])
        for name in ("href", "src"):
            if attributes.get(name):
                self.references.append(attributes[name])


def parse(page: Path) -> PageParser:
    parser = PageParser()
    parser.feed(page.read_text(encoding="utf-8"))
    return parser


def page_id(page: Path) -> str:
    return str(page.relative_to(ROOT))


@pytest.mark.parametrize("page", HTML_FILES, ids=page_id)
def test_page_has_language_and_title(page):
    parsed = parse(page)

    assert parsed.lang == "es"
    assert parsed.has_title


@pytest.mark.parametrize("page", HTML_FILES, ids=page_id)
def test_local_links_and_assets_exist(page):
    parsed = parse(page)
    missing = []

    for reference in parsed.references:
        url = urlparse(reference)
        if url.scheme or reference.startswith("//"):
            continue
        if url.path:
            target = page.parent / url.path
            if not target.is_file():
                missing.append(reference)
                continue
        else:
            target = page
        if url.fragment and url.fragment not in parse(target).ids:
            missing.append(reference)

    assert not missing, f"Referencias rotas en {page.name}: {missing}"


@pytest.mark.parametrize("script", JS_FILES, ids=page_id)
def test_javascript_syntax(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js no está instalado")

    result = subprocess.run([node, "--check", str(script)], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
