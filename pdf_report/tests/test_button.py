"""Import + helper tests for PdfReportButton.

The browser capture flow (html2canvas + ECharts getDataURL) is not
covered here — it's exercised via the per-app manual smoke test.
"""

import json


def test_module_imports():
    from pdf_report.button import PdfReportButton  # noqa: F401


def test_serialize_capture_specs_map_and_echart():
    from pdf_report.button import _serialize_capture_specs
    from pdf_report.models import (
        EChartCapture,
        LegendCapture,
        MapCapture,
        StatsTableCapture,
    )

    captures = [
        MapCapture(selector=".m"),
        EChartCapture(selector=".c1", optional=False, pixel_ratio=2),
        EChartCapture(selector=".c2", optional=True, pixel_ratio=3),
        LegendCapture(legend_data={}),   # native; not serialized
        StatsTableCapture(rows=()),       # native; not serialized
    ]
    payload = json.loads(_serialize_capture_specs(captures))
    assert payload == [
        {"kind": "map", "selector": ".m"},
        {"kind": "echart", "selector": ".c1", "optional": False, "pixel_ratio": 2},
        {"kind": "echart", "selector": ".c2", "optional": True, "pixel_ratio": 3},
    ]


def test_decode_image_map_strips_data_url_prefix_and_sentinels():
    import base64

    from pdf_report.button import _decode_image_map

    raw = b"hello"
    b64 = base64.b64encode(raw).decode("ascii")
    captured = {
        ".x": f"data:image/png;base64,{b64}",
        ".y": b64,  # without prefix
        "__error__": "nope",
    }
    out = _decode_image_map(captured)
    assert out == {".x": raw, ".y": raw}
