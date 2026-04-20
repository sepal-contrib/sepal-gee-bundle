"""PdfReportButton — Solara trigger for the pdf_report capture pipeline.

Flow:
    click → set building=True and bump a capture ``tick``
         → a hidden VuetifyTemplate lazy-loads html2canvas, walks the
           capture spec list, writes a ``{selector: dataURL}`` dict
           into ``captured_images`` traitlet
         → a solara.use_effect sees the dict change, base64-decodes it,
           calls build_pdf_report(), base64-encodes the result, and sets
           a ``pdf_base64`` + ``download_tick`` pair on the template
         → the template's JS watcher on ``download_tick`` creates a
           Blob anchor and auto-clicks it to download the PDF.

Error surface: any failure in the JS phase writes ``__error__`` into
``captured_images``; Python surfaces the message via the pysepal
notification system if present, else via the module logger.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Sequence

import ipyvuetify as ipv
import reacton.ipyvuetify as rv
import solara
from traitlets import Dict, Int, Unicode

from pysepal.solara.notifications import use_notifications
from pysepal.solara.notifications.notifier import NoopNotifier

from .builder import build_pdf_report
from .models import (
    CaptureSpec,
    EChartCapture,
    MapCapture,
    PdfReportConfig,
)

log = logging.getLogger(__name__)

_HTML2CANVAS_URL = "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"

_CAPTURE_TEMPLATE = """
<script class="pdf-report-capture">
{
    data() {
        return { _pysepal_busy: false };
    },
    watch: {
        tick() { this._runCapture(); },
        download_tick() { this._triggerDownload(); }
    },
    methods: {
        _log(msg) {
            const text = '[pdf_report] ' + String(msg);
            try { console.log(text); } catch (_e) {}
            this.log_message = text;
            this.log_tick = (this.log_tick || 0) + 1;
        },
        _loadHtml2Canvas() {
            const self = this;
            if (typeof window.html2canvas === 'function') {
                self._log('html2canvas already present');
                return Promise.resolve(window.html2canvas);
            }
            if (window.__pysepal_h2c_promise__) {
                self._log('html2canvas load already in-flight');
                return window.__pysepal_h2c_promise__;
            }
            self._log('injecting html2canvas script from __H2C_URL__');
            window.__pysepal_h2c_promise__ = new Promise((resolve, reject) => {
                const s = document.createElement('script');
                s.src = '__H2C_URL__';
                s.crossOrigin = 'anonymous';
                s.onload = () => {
                    const t = typeof window.html2canvas;
                    self._log('html2canvas script onload fired; typeof window.html2canvas = ' + t);
                    if (t === 'function') {
                        resolve(window.html2canvas);
                    } else {
                        reject(new Error(
                            'html2canvas script loaded but window.html2canvas is ' + t +
                            ' (CSP, ad-blocker, or CDN mismatch?)'
                        ));
                    }
                };
                s.onerror = (ev) => {
                    self._log('html2canvas script onerror fired');
                    reject(new Error('failed to load html2canvas from CDN'));
                };
                document.head.appendChild(s);
            });
            return window.__pysepal_h2c_promise__;
        },
        async _waitForTiles(root, timeoutMs) {
            const deadline = Date.now() + timeoutMs;
            let lastCount = -1;
            while (Date.now() < deadline) {
                const tiles = root.querySelectorAll('.leaflet-tile');
                const loaded = root.querySelectorAll('.leaflet-tile-loaded');
                if (loaded.length !== lastCount) {
                    this._log('tile wait: ' + loaded.length + ' / ' + tiles.length + ' loaded');
                    lastCount = loaded.length;
                }
                if (tiles.length === 0) return;
                if (loaded.length === tiles.length) return;
                await new Promise(r => setTimeout(r, 150));
            }
            this._log('tile wait: deadline reached, proceeding');
        },
        async _withTimeout(p, ms, label) {
            let to;
            const timeout = new Promise((_, reject) => {
                to = setTimeout(() => reject(new Error(label + ' timed out')), ms);
            });
            try { return await Promise.race([p, timeout]); }
            finally { clearTimeout(to); }
        },
        async _captureMap(spec) {
            this._log('map capture start: ' + spec.selector);
            const h2c = await this._loadHtml2Canvas();
            if (typeof h2c !== 'function') {
                throw new Error('html2canvas not callable after load (typeof = ' + (typeof h2c) + ')');
            }
            const el = document.querySelector(spec.selector);
            if (!el) throw new Error('map selector not found: ' + spec.selector);
            this._log('map element found (rect ' + el.clientWidth + 'x' + el.clientHeight + ')');
            await this._waitForTiles(el, 5000);
            const canvas = await this._withTimeout(
                h2c(el, { useCORS: true, backgroundColor: '#ffffff', scale: 2, logging: false }),
                15000,
                'map capture ' + spec.selector
            );
            this._log('map capture complete: ' + spec.selector + ' (' + canvas.width + 'x' + canvas.height + ')');
            return canvas.toDataURL('image/png');
        },
        async _findEchartsInstance(el) {
            const deadline = Date.now() + 500;
            while (Date.now() < deadline) {
                if (window.echarts) {
                    let inst = window.echarts.getInstanceByDom(el);
                    if (!inst) {
                        const child = el.querySelector('[_echarts_instance_]');
                        if (child) inst = window.echarts.getInstanceByDom(child);
                    }
                    if (inst) return inst;
                }
                await new Promise(r => setTimeout(r, 50));
            }
            return null;
        },
        async _captureEchart(spec) {
            this._log('echart capture start: ' + spec.selector);
            const el = document.querySelector(spec.selector);
            if (!el) {
                if (spec.optional) {
                    this._log('echart optional selector missing, skipping: ' + spec.selector);
                    return null;
                }
                throw new Error('echart selector not found: ' + spec.selector);
            }
            const inst = await this._findEchartsInstance(el);
            if (!inst) {
                if (spec.optional) {
                    this._log('echart optional instance missing, skipping: ' + spec.selector);
                    return null;
                }
                throw new Error('ECharts instance not found for selector: ' + spec.selector);
            }
            const url = inst.getDataURL({
                pixelRatio: spec.pixel_ratio || 2,
                backgroundColor: '#ffffff',
            });
            this._log('echart capture complete: ' + spec.selector);
            return url;
        },
        async _runCapture() {
            if (this._pysepal_busy) {
                this._log('runCapture ignored (already busy)');
                return;
            }
            this._pysepal_busy = true;
            this._log('runCapture start');
            let specs = [];
            try { specs = JSON.parse(this.capture_specs || '[]'); }
            catch (_e) { specs = []; }
            this._log('runCapture specs: ' + specs.length);
            const results = {};
            try {
                for (const spec of specs) {
                    let url = null;
                    if (spec.kind === 'map') url = await this._captureMap(spec);
                    else if (spec.kind === 'echart') url = await this._captureEchart(spec);
                    if (url) results[spec.selector] = url;
                }
                this._log('runCapture done, ' + Object.keys(results).length + ' images');
                this.captured_images = results;
            } catch (e) {
                const msg = (e && (e.stack || e.message)) || String(e);
                this._log('runCapture error: ' + msg);
                this.captured_images = { __error__: String(e && e.message || e) };
            } finally {
                this._pysepal_busy = false;
            }
        },
        _triggerDownload() {
            const b64 = this.pdf_base64;
            if (!b64) return;
            this._log('triggering download: ' + (this.filename || 'report.pdf') + ' (' + b64.length + ' b64 chars)');
            const link = document.createElement('a');
            link.href = 'data:application/pdf;base64,' + b64;
            link.download = this.filename || 'report.pdf';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
}
</script>
""".replace("__H2C_URL__", _HTML2CANVAS_URL)


class _CaptureTemplate(ipv.VuetifyTemplate):
    tick = Int(0).tag(sync=True)
    capture_specs = Unicode("[]").tag(sync=True)
    captured_images = Dict({}).tag(sync=True)
    pdf_base64 = Unicode("").tag(sync=True)
    download_tick = Int(0).tag(sync=True)
    filename = Unicode("report.pdf").tag(sync=True)
    log_message = Unicode("").tag(sync=True)
    log_tick = Int(0).tag(sync=True)
    template = Unicode(_CAPTURE_TEMPLATE).tag(sync=True)


def _serialize_capture_specs(captures: Sequence[CaptureSpec]) -> str:
    """Serialize only the capture specs that need browser-side capture."""
    payload: list[dict] = []
    for c in captures:
        if isinstance(c, MapCapture):
            payload.append({"kind": "map", "selector": c.selector})
        elif isinstance(c, EChartCapture):
            payload.append(
                {
                    "kind": "echart",
                    "selector": c.selector,
                    "optional": c.optional,
                    "pixel_ratio": c.pixel_ratio,
                }
            )
        # LegendCapture / StatsTableCapture are rendered natively; not serialized.
    return json.dumps(payload)


def _decode_image_map(captured: dict[str, str]) -> dict[str, bytes]:
    """Strip data-URL prefixes and base64-decode. Sentinel keys (``__*``) are dropped."""
    out: dict[str, bytes] = {}
    for sel, data_url in captured.items():
        if sel.startswith("__"):
            continue
        if not isinstance(data_url, str) or not data_url:
            continue
        b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
        out[sel] = base64.b64decode(b64)
    return out


@solara.component
def PdfReportButton(
    filename: str,
    config: PdfReportConfig,
    captures: Sequence[CaptureSpec],
    label: str = "Download PDF",
    icon_name: str = "mdi-file-pdf-box",
    color: str = "primary",
    block: bool = False,
    small: bool = True,
    classes: Sequence[str] = (),
) -> None:
    """Render a button that captures map+charts and downloads a PDF."""

    building = solara.use_reactive(False)
    captured_state = solara.use_reactive({})
    captures_list = list(captures)

    capture_engine = solara.use_memo(lambda: _CaptureTemplate(), [])
    capture_engine.filename = filename
    capture_engine.capture_specs = _serialize_capture_specs(captures_list)

    notifications = use_notifications()
    has_notifications = not isinstance(notifications, NoopNotifier)

    def _notify_error(msg: str) -> None:
        if has_notifications:
            notifications.error(msg)
        log.error(msg)

    def _observe():
        def _on_change(change: dict) -> None:
            new = change.get("new") or {}
            captured_state.set(dict(new))

        def _on_log(_change: dict) -> None:
            msg = capture_engine.log_message
            if not msg:
                return
            # stdout so it always surfaces in `solara run` output, even if
            # no logger handler is configured at the bundle level.
            print(msg, flush=True)
            log.info(msg)

        capture_engine.observe(_on_change, names="captured_images")
        capture_engine.observe(_on_log, names="log_tick")
        def _cleanup():
            capture_engine.unobserve(_on_change, names="captured_images")
            capture_engine.unobserve(_on_log, names="log_tick")
        return _cleanup

    solara.use_effect(_observe, [])

    def _handle_captured() -> None:
        captured = captured_state.value or {}
        if not captured:
            return
        try:
            if "__error__" in captured:
                _notify_error(f"PDF capture failed: {captured['__error__']}")
                return
            image_bytes = _decode_image_map(captured)
            pdf_bytes = build_pdf_report(config, captures_list, image_bytes)
            capture_engine.pdf_base64 = base64.b64encode(pdf_bytes).decode("ascii")
            capture_engine.download_tick = capture_engine.download_tick + 1
        except Exception as exc:  # noqa: BLE001 - user-facing error surface
            log.exception("PDF build failed")
            _notify_error(f"PDF build failed: {exc}")
        finally:
            building.set(False)
            captured_state.set({})
            capture_engine.captured_images = {}

    solara.use_effect(_handle_captured, [captured_state.value])

    def _start() -> None:
        if building.value:
            return
        building.set(True)
        capture_engine.tick = capture_engine.tick + 1

    solara.Button(
        label=label,
        icon_name=icon_name,
        on_click=_start,
        color=color,
        block=block,
        small=small,
        disabled=building.value,
        classes=list(classes),
    )

    rv.Html(tag="div", children=[capture_engine], style_="display:none;")


__all__ = ["PdfReportButton"]
