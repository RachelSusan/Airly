"""Static accessibility and CSP checks on the frontend shell (see docs/accessibility.md)."""

from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import STATIC_DIR, create_app

INDEX = STATIC_DIR / "index.html"


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))


@pytest.fixture(scope="module")
def tags() -> list[tuple[str, dict[str, str | None]]]:
    parser = _Collector()
    parser.feed(INDEX.read_text(encoding="utf-8"))
    return parser.tags


def test_html_has_language(tags) -> None:
    html = next(attrs for tag, attrs in tags if tag == "html")
    assert html.get("lang") == "en"


def test_landmarks_and_skip_link(tags) -> None:
    names = {tag for tag, _ in tags}
    assert {"header", "nav", "main", "footer"} <= names
    assert any(tag == "a" and attrs.get("class") == "skip-link" for tag, attrs in tags)


def test_every_input_has_a_label(tags) -> None:
    label_targets = {attrs.get("for") for tag, attrs in tags if tag == "label"}
    for tag, attrs in tags:
        if tag in {"input", "select", "textarea"}:
            assert attrs.get("id") in label_targets or attrs.get("aria-label"), attrs


def test_decorative_svgs_are_hidden(tags) -> None:
    for tag, attrs in tags:
        if tag == "svg":
            assert attrs.get("aria-hidden") == "true"


def test_no_inline_scripts_or_styles() -> None:
    parser = _Collector()
    parser.feed(INDEX.read_text(encoding="utf-8"))
    for tag, attrs in parser.tags:
        assert "style" not in attrs
        assert not any(name.startswith("on") for name in attrs)
        if tag == "script":
            assert attrs.get("src"), "inline <script> would be blocked by the CSP"


def test_frontend_never_uses_inner_html() -> None:
    for path in Path(STATIC_DIR, "js").rglob("*.js"):
        assert "innerHTML" not in path.read_text(encoding="utf-8"), path


def test_index_served_with_csp() -> None:
    with TestClient(create_app(Settings(gemini_api_key=None))) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "Content-Security-Policy" in response.headers
