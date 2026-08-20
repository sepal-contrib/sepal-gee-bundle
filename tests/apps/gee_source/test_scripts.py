"""Tests for the gee_source pure helpers."""

from __future__ import annotations

from pathlib import PurePosixPath
from types import SimpleNamespace
from typing import NamedTuple
from unittest.mock import patch

import pytest

from apps.gee_source.scripts.extract import (
    extract_js_source,
    parse_init_urls,
)
from apps.gee_source.scripts.highlight import highlight_css, highlight_javascript
from apps.gee_source.scripts.save import sanitize_filename, save_code

# --------------------------------------------------------------------------- #
# parse_init_urls                                                              #
# --------------------------------------------------------------------------- #


class TestParseInitUrls:
    def test_returns_empty_for_page_without_scripts(self):
        assert parse_init_urls("<html><body>hi</body></html>") == []

    def test_extracts_https_init_url(self):
        html = """
            <html><body>
              <script>
                init("https://earthengine.googleapis.com/foo/bar.json");
              </script>
            </body></html>
        """
        assert parse_init_urls(html) == ["https://earthengine.googleapis.com/foo/bar.json"]

    def test_skips_non_https_init_calls(self):
        html = """
            <script>init("relative/path.json");</script>
            <script>init("http://insecure.example/x.json");</script>
        """
        assert parse_init_urls(html) == []

    def test_ignores_non_init_scripts(self):
        html = """
            <script>window.foo = 1;</script>
            <script>init("https://a.example/x.json");</script>
        """
        assert parse_init_urls(html) == ["https://a.example/x.json"]

    def test_handles_multiple_init_scripts(self):
        html = """
            <script>init("https://a.example/x.json");</script>
            <script>init("https://b.example/y.json");</script>
        """
        assert parse_init_urls(html) == [
            "https://a.example/x.json",
            "https://b.example/y.json",
        ]


# --------------------------------------------------------------------------- #
# extract_js_source                                                            #
# --------------------------------------------------------------------------- #


def _fake_response(json_payload=None, text=""):
    return SimpleNamespace(
        json=lambda: json_payload,
        text=text,
        raise_for_status=lambda: None,
    )


class TestExtractJsSource:
    def test_rejects_non_https_url(self):
        with pytest.raises(ValueError):
            extract_js_source("ftp://example.com")

    def test_rejects_empty_url(self):
        with pytest.raises(ValueError):
            extract_js_source("")

    def test_returns_dependency_code(self):
        html = '<html><script>init("https://api.example/init.json");</script></html>'
        payload = {
            "path": "main",
            "dependencies": {"main": "print('hello');"},
        }

        with patch(
            "apps.gee_source.scripts.extract.requests.get",
            return_value=_fake_response(text=html),
        ):
            result = extract_js_source(
                "https://user.users.earthengine.app/view/demo",
                fetcher=lambda url: _fake_response(json_payload=payload),
            )

        assert result == "print('hello');"

    def test_concatenates_multiple_init_payloads(self):
        html = (
            '<script>init("https://api.example/a.json");</script>'
            '<script>init("https://api.example/b.json");</script>'
        )
        payloads = {
            "https://api.example/a.json": {
                "path": "m1",
                "dependencies": {"m1": "A();"},
            },
            "https://api.example/b.json": {
                "path": "m2",
                "dependencies": {"m2": "B();"},
            },
        }

        with patch(
            "apps.gee_source.scripts.extract.requests.get",
            return_value=_fake_response(text=html),
        ):
            result = extract_js_source(
                "https://user.users.earthengine.app/view/demo",
                fetcher=lambda url: _fake_response(json_payload=payloads[url]),
            )

        assert result == "A();\nB();"

    def test_returns_empty_when_no_init_url_found(self):
        html = "<html><body>nothing here</body></html>"
        with patch(
            "apps.gee_source.scripts.extract.requests.get",
            return_value=_fake_response(text=html),
        ):
            result = extract_js_source(
                "https://user.users.earthengine.app/view/demo",
                fetcher=lambda url: _fake_response(json_payload={}),
            )
        assert result == ""

    def test_returns_empty_when_payload_missing_path(self):
        html = '<script>init("https://api.example/x.json");</script>'
        with patch(
            "apps.gee_source.scripts.extract.requests.get",
            return_value=_fake_response(text=html),
        ):
            result = extract_js_source(
                "https://user.users.earthengine.app/view/demo",
                fetcher=lambda url: _fake_response(json_payload={"dependencies": {"other": "x"}}),
            )
        assert result == ""


# --------------------------------------------------------------------------- #
# highlight                                                                    #
# --------------------------------------------------------------------------- #


class TestHighlight:
    def test_empty_code_returns_empty(self):
        assert highlight_javascript("") == ""

    def test_wraps_output_in_styled_div(self):
        html = highlight_javascript("var x = 1;")
        assert '<div class="highlight pa-3 mt-2"' in html
        assert "var" in html

    def test_css_is_non_empty(self):
        css = highlight_css()
        assert ".highlight" in css
        assert len(css) > 50


# --------------------------------------------------------------------------- #
# sanitize_filename                                                            #
# --------------------------------------------------------------------------- #


class TestSanitizeFilename:
    def test_empty_returns_default(self):
        assert sanitize_filename("") == "gee_source"

    def test_strips_directories(self):
        assert sanitize_filename("/tmp/my-app") == "my-app"

    def test_removes_trailing_js_extension(self):
        assert sanitize_filename("my-app.js") == "my-app"
        assert sanitize_filename("my-app.JS") == "my-app"

    def test_replaces_unsafe_chars(self):
        assert sanitize_filename("my app (v2)!") == "my_app_v2"

    def test_collapses_underscores_and_trims(self):
        assert sanitize_filename("__a**b__") == "a_b"

    def test_all_unsafe_returns_default(self):
        assert sanitize_filename("!!!") == "gee_source"


# --------------------------------------------------------------------------- #
# save_code                                                                    #
# --------------------------------------------------------------------------- #

RESULTS_DIR = "/home/sepal-user/module_results/sepal_gee_bundle.gee_source"


class FakeEntry(NamedTuple):
    """Stands in for pysepal_api's FileEntry; save_code only reads ``name``."""

    name: str
    path: str


class FakeUserFiles:
    """In-memory stand-in for ``SepalClient.files``."""

    def __init__(self):
        self.stored = {}

    def list(self, folder=".", *, extensions=None, include_hidden=False):
        prefix = f"{str(folder).rstrip('/')}/"
        return [
            FakeEntry(name=path.rsplit("/", 1)[-1], path=path)
            for path in sorted(self.stored)
            if path.startswith(prefix)
        ]

    def write(self, file_path, content, *, overwrite=False):
        if file_path in self.stored and not overwrite:
            raise AssertionError("save_code should preflight existing files")
        self.stored[file_path] = content.encode("utf-8") if isinstance(content, str) else content
        return {}


class FakeSepalClient:
    """Small in-memory fake for SepalClient user-files calls."""

    def __init__(self):
        self.files = FakeUserFiles()
        self.results_dirs_created = 0

    def ensure_results_dir(self):
        self.results_dirs_created += 1
        return PurePosixPath(RESULTS_DIR)


class TestSaveCode:
    def test_writes_file_with_js_extension(self):
        sepal_client = FakeSepalClient()

        path = save_code("console.log('hi');", "demo", sepal_client=sepal_client)

        assert path == f"{RESULTS_DIR}/demo.js"
        assert sepal_client.files.stored[path] == b"console.log('hi');"
        assert sepal_client.results_dirs_created == 1

    def test_sanitizes_filename_before_writing(self):
        sepal_client = FakeSepalClient()
        path = save_code("x;", "my app!", sepal_client=sepal_client)
        assert path.endswith("/my_app.js")

    def test_refuses_to_overwrite(self):
        sepal_client = FakeSepalClient()
        save_code("first", "demo", sepal_client=sepal_client)
        with pytest.raises(ValueError, match="already exists"):
            save_code("second", "demo", sepal_client=sepal_client)

    def test_refuses_empty_code(self):
        with pytest.raises(ValueError, match="empty"):
            save_code("", "demo", sepal_client=FakeSepalClient())

    def test_requires_sepal_client(self):
        with pytest.raises(ValueError, match="SEPAL session"):
            save_code("x;", "demo", sepal_client=None)
