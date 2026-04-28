"""Central-area iframe that renders either the live EE App or its source."""

from __future__ import annotations

import ipyvuetify as v
import traitlets


class SourceIframe(v.VuetifyTemplate):
    """Single iframe widget driven by Python-side traits.

    Three reactive traits control what the iframe shows:

    * ``mode`` — ``"app"`` (live URL) or ``"source"`` (highlighted HTML).
    * ``app_url`` — set when an extract has succeeded; used in app mode.
    * ``srcdoc`` — full HTML document with pygments CSS + highlighted code.

    When the relevant value is empty for the active mode, a placeholder
    HTML string is rendered instead so the central area never goes blank.
    """

    mode = traitlets.Unicode("app").tag(sync=True)
    app_url = traitlets.Unicode("").tag(sync=True)
    srcdoc = traitlets.Unicode("").tag(sync=True)
    placeholder = traitlets.Unicode(
        "<!doctype html><html><body style='margin:0;display:flex;"
        "align-items:center;justify-content:center;height:100vh;"
        "font-family:Roboto,sans-serif;color:#888;background:#fafafa'>"
        "<div style='text-align:center'>"
        "<div style='font-size:48px;margin-bottom:8px'>&#127757;</div>"
        "<div>Paste an Earth Engine App URL and press <b>Extract</b>.</div>"
        "</div></body></html>"
    ).tag(sync=True)

    template = traitlets.Unicode(
        """
<template>
  <div
    :style="{
      position: 'fixed',
      top: '0',
      bottom: '0',
      left: 'var(--drawer-width, 0px)',
      right: 'calc(var(--right-panel-open, 0) * var(--right-panel-width, 0px))',
      background: '#000',
      transition: 'left 0.3s ease, right 0.3s ease',
      zIndex: 0,
    }"
  >
    <iframe
      v-if="mode === 'app' && app_url"
      :src="app_url"
      style="width:100%; height:100%; border:none; background:white; display:block;"
      sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
    ></iframe>
    <iframe
      v-else-if="mode === 'source' && srcdoc"
      :srcdoc="srcdoc"
      style="width:100%; height:100%; border:none; background:white; display:block;"
      sandbox="allow-same-origin"
    ></iframe>
    <iframe
      v-else
      :srcdoc="placeholder"
      style="width:100%; height:100%; border:none; display:block;"
    ></iframe>
  </div>
</template>
"""
    ).tag(sync=True)


def build_source_srcdoc(highlighted_html: str, css: str) -> str:
    """Wrap pygments output in a self-contained HTML document.

    The iframe's ``srcdoc`` attribute scopes the pygments stylesheet from
    the rest of the page. Returns ``""`` when there is no source so the
    widget falls back to the placeholder.
    """
    if not highlighted_html:
        return ""
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>"
        "html,body{margin:0;padding:0;height:100%;background:#f8f8f8;"
        "font-family:Menlo,Consolas,monospace;font-size:13px;}"
        ".highlight{padding:12px;min-height:100%;box-sizing:border-box;}"
        ".highlight pre{margin:0;}"
        f"{css}"
        "</style></head><body>"
        f"{highlighted_html}"
        "</body></html>"
    )
