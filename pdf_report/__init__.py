"""Reusable PDF report export for pysepal Solara apps.

Captures the live ipyleaflet map (via html2canvas) and ECharts widgets
(via getDataURL) in the browser, and composes a single long-page PDF in
Python with reportlab. Legends are re-drawn natively (vector) from the
same LegendData dataclass used by LegendComponent — no DOM capture for
the legend.

Public API is re-exported here; see the submodules for implementation.
"""
