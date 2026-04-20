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
import ipyvuetify as v
import reacton.ipyvuetify as rv
import solara
from pysepal.solara.notifications import use_notifications
from pysepal.solara.notifications.notifier import NoopNotifier
from reacton import ipyvue
from traitlets import Dict, Int, Unicode

from .builder import build_pdf_report
from .models import (
    CaptureSpec,
    EChartCapture,
    MapCapture,
    PdfReportConfig,
)

log = logging.getLogger("sepalui.pdf_report")

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
            // We run inside jupyter-vue, which provides RequireJS / AMD.
            // html2canvas is UMD and registers as an AMD module when define.amd
            // is present, so a plain <script src=...> never attaches it to
            // window.html2canvas. We fetch the source as text and execute it
            // with `define` temporarily shadowed, forcing the UMD fallback
            // that sets root.html2canvas.
            self._log('fetching html2canvas source from __H2C_URL__');
            window.__pysepal_h2c_promise__ = (async () => {
                let response;
                try {
                    response = await fetch('__H2C_URL__', { credentials: 'omit' });
                } catch (e) {
                    throw new Error('html2canvas fetch failed: ' + (e && e.message || e));
                }
                if (!response.ok) {
                    throw new Error('html2canvas fetch HTTP ' + response.status);
                }
                const source = await response.text();
                self._log('html2canvas source fetched (' + source.length + ' bytes); executing with AMD disabled');
                const savedDefine = window.define;
                const savedExports = window.exports;
                const savedModule = window.module;
                try {
                    // Hide AMD + CommonJS so UMD falls through to window.html2canvas.
                    window.define = undefined;
                    window.exports = undefined;
                    window.module = undefined;
                    (new Function(source)).call(window);
                } finally {
                    window.define = savedDefine;
                    window.exports = savedExports;
                    window.module = savedModule;
                }
                const t = typeof window.html2canvas;
                self._log('html2canvas executed; typeof window.html2canvas = ' + t);
                if (t !== 'function') {
                    throw new Error('html2canvas failed to register on window (typeof = ' + t + ')');
                }
                return window.html2canvas;
            })();
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
        _collectLeafletSvgOverlays(target) {
            // Snapshot each SVG overlay's current rendering box and serialized
            // XML while it's still positioned correctly via Leaflet's transform.
            const targetRect = target.getBoundingClientRect();
            const overlays = [];
            const svgs = target.querySelectorAll(
                '.leaflet-overlay-pane svg, .leaflet-shadow-pane svg'
            );
            const serializer = new XMLSerializer();
            for (const svg of svgs) {
                const rect = svg.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) continue;
                // Ensure standalone SVG: inject xmlns if missing.
                const clone = svg.cloneNode(true);
                if (!clone.getAttribute('xmlns')) {
                    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
                }
                if (!clone.getAttribute('xmlns:xlink')) {
                    clone.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink');
                }
                // Force an explicit width/height matching the bounding box so the
                // Image element rasterizes at the right pixel size.
                clone.setAttribute('width', String(rect.width));
                clone.setAttribute('height', String(rect.height));
                // Drop the CSS transform on the clone — we position via canvas draw.
                clone.style.transform = 'none';
                clone.style.left = '0';
                clone.style.top = '0';
                overlays.push({
                    el: svg,
                    xml: serializer.serializeToString(clone),
                    x: rect.left - targetRect.left,
                    y: rect.top - targetRect.top,
                    width: rect.width,
                    height: rect.height,
                });
            }
            return overlays;
        },
        _rasterizeSvgOverlay(overlay, scale) {
            return new Promise((resolve, reject) => {
                const dataUrl = 'data:image/svg+xml;charset=utf-8,' +
                    encodeURIComponent(overlay.xml);
                const img = new Image();
                img.decoding = 'sync';
                img.onload = () => resolve({ overlay, img });
                img.onerror = (e) => reject(new Error(
                    'svg overlay rasterize failed: ' + (e && e.message || 'load error')
                ));
                img.src = dataUrl;
            });
        },
        async _captureMap(spec) {
            this._log('map capture start: ' + spec.selector);
            const h2c = await this._loadHtml2Canvas();
            if (typeof h2c !== 'function') {
                throw new Error('html2canvas not callable after load (typeof = ' + (typeof h2c) + ')');
            }
            const wrapper = document.querySelector(spec.selector);
            if (!wrapper) throw new Error('map selector not found: ' + spec.selector);
            // SepalMap in fullscreen mode wraps a position:fixed .leaflet-container
            // that's hoisted out of the wrapper's layout. The wrapper itself
            // measures 0x0 — capture the fixed child instead.
            let target = wrapper;
            const leaflet = wrapper.querySelector('.leaflet-container');
            if (leaflet && (leaflet !== wrapper)) {
                this._log(
                    'map: using .leaflet-container child (' +
                    leaflet.clientWidth + 'x' + leaflet.clientHeight +
                    ') instead of wrapper (' +
                    wrapper.clientWidth + 'x' + wrapper.clientHeight + ')'
                );
                target = leaflet;
            }
            await this._waitForTiles(target, 5000);

            // Collect SVG overlays BEFORE hiding them (getBoundingClientRect
            // needs them visible). Then hide during html2canvas to avoid its
            // SVG-transform mis-rendering bug. Re-draw them onto the captured
            // canvas ourselves using native Image + drawImage — this uses the
            // browser's own SVG rasterizer, which honors transforms correctly.
            const overlays = this._collectLeafletSvgOverlays(target);
            this._log('collected ' + overlays.length + ' leaflet SVG overlay(s)');
            const savedDisplay = overlays.map(o => ({ el: o.el, display: o.el.style.display }));
            for (const s of savedDisplay) s.el.style.display = 'none';

            const scale = 2;
            let mapCanvas;
            try {
                mapCanvas = await this._withTimeout(
                    h2c(target, { useCORS: true, backgroundColor: '#ffffff', scale, logging: false }),
                    15000,
                    'map capture ' + spec.selector
                );
            } finally {
                for (const s of savedDisplay) s.el.style.display = s.display;
            }
            this._log('map tiles captured (' + mapCanvas.width + 'x' + mapCanvas.height + ')');

            // Composite each SVG overlay onto the captured canvas.
            if (overlays.length > 0) {
                const ctx = mapCanvas.getContext('2d');
                const rasters = await Promise.all(
                    overlays.map(o => this._rasterizeSvgOverlay(o, scale).catch(err => {
                        this._log('overlay rasterize failed, skipping: ' + err.message);
                        return null;
                    }))
                );
                for (const r of rasters) {
                    if (!r) continue;
                    ctx.drawImage(
                        r.img,
                        r.overlay.x * scale,
                        r.overlay.y * scale,
                        r.overlay.width * scale,
                        r.overlay.height * scale
                    );
                }
                this._log('composited ' + rasters.filter(Boolean).length + ' overlay(s) onto map canvas');
            }

            this._log('map capture complete: ' + spec.selector + ' (' + mapCanvas.width + 'x' + mapCanvas.height + ')');
            return mapCanvas.toDataURL('image/png');
        },
        _findEchartsInstanceSync(root) {
            // Try multiple strategies:
            //   1. Walk root + descendants and call window.echarts.getInstanceByDom
            //   2. Find any [_echarts_instance_] marker and resolve by id
            //   3. Inspect elements for the internal __ECHARTS_INSTANCE__ property
            const all = [root, ...root.querySelectorAll('*')];
            if (window.echarts && typeof window.echarts.getInstanceByDom === 'function') {
                for (const el of all) {
                    const inst = window.echarts.getInstanceByDom(el);
                    if (inst) return inst;
                }
                const marked = root.querySelector('[_echarts_instance_]');
                if (marked && typeof window.echarts.getInstanceById === 'function') {
                    const id = marked.getAttribute('_echarts_instance_');
                    const inst = window.echarts.getInstanceById(id);
                    if (inst) return inst;
                }
            }
            for (const el of all) {
                if (el.__ECHARTS_INSTANCE__) return el.__ECHARTS_INSTANCE__;
            }
            return null;
        },
        async _findEchartsInstance(root) {
            const deadline = Date.now() + 1000;
            while (Date.now() < deadline) {
                const inst = this._findEchartsInstanceSync(root);
                if (inst) return inst;
                await new Promise(r => setTimeout(r, 100));
            }
            return null;
        },
        async _rasterizeElement(el, label) {
            this._log(label + ': falling back to html2canvas rasterization');
            const h2c = await this._loadHtml2Canvas();
            const canvas = await this._withTimeout(
                h2c(el, { useCORS: true, backgroundColor: '#ffffff', scale: 2, logging: false }),
                15000,
                label
            );
            return canvas.toDataURL('image/png');
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
            this._log(
                'echart element found (rect ' + el.clientWidth + 'x' + el.clientHeight +
                '; descendants=' + el.querySelectorAll('*').length +
                '; typeof window.echarts=' + (typeof window.echarts) + ')'
            );
            const inst = await this._findEchartsInstance(el);
            if (inst) {
                const url = inst.getDataURL({
                    pixelRatio: spec.pixel_ratio || 2,
                    backgroundColor: '#ffffff',
                });
                this._log('echart capture via getDataURL: ' + spec.selector);
                return url;
            }
            // No instance — grab the native <canvas> directly. This preserves
            // ECharts' own devicePixelRatio-scaled pixel buffer, which is much
            // sharper than re-rasterizing the container with html2canvas.
            const canvases = el.querySelectorAll('canvas');
            if (canvases.length > 0) {
                // Pick the largest canvas (ECharts may render hover/zr layers too).
                let best = canvases[0];
                for (const c of canvases) {
                    if (c.width * c.height > best.width * best.height) best = c;
                }
                try {
                    const url = best.toDataURL('image/png');
                    this._log(
                        'echart capture via canvas.toDataURL (' +
                        best.width + 'x' + best.height + '): ' + spec.selector
                    );
                    return url;
                } catch (e) {
                    this._log('canvas.toDataURL failed (' + (e && e.message) + '), falling back to html2canvas');
                }
            } else {
                this._log('no <canvas> found inside ' + spec.selector + ', falling back to html2canvas');
            }
            try {
                const url = await this._rasterizeElement(el, 'echart rasterize ' + spec.selector);
                this._log('echart capture via html2canvas: ' + spec.selector);
                return url;
            } catch (e) {
                if (spec.optional) {
                    this._log('echart optional rasterize failed, skipping: ' + spec.selector);
                    return null;
                }
                throw e;
            }
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
        except Exception as exc:
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

    # Build children: a small spinner to the left of the label while capturing,
    # plus the optional leading icon when idle. We avoid Vuetify's native
    # `loading` prop — it hides children and reports inconsistent disabled
    # state — and wire clicks via ipyvue.use_event (the reacton-compatible
    # way; `rv.Btn(on_click=...)` is silently ignored).
    btn_children: list = []
    if building.value:
        spinner_size = 14 if small else 16
        btn_children.append(
            v.ProgressCircular(
                size=spinner_size,
                width=2,
                color="white",
                indeterminate=True,
                class_="mr-2",
            )
        )
    elif icon_name:
        btn_children.append(v.Icon(left=True, small=small, children=[icon_name]))
    btn_children.append(label)

    btn = rv.Btn(
        color=color,
        block=block,
        small=small,
        disabled=building.value,
        class_=" ".join(classes) if classes else "",
        children=btn_children,
    )
    ipyvue.use_event(btn, "click", lambda *_ignore: _start())

    rv.Html(tag="div", children=[capture_engine], style_="display:none;")


__all__ = ["PdfReportButton"]
