"""Tests for LegendData serialization."""

from dataclasses import asdict

from pysepal.solara.components.legend import (
    DiscreteEntry,
    GradientEntry,
    LegendData,
)


def test_empty_legend_serializes():
    data = LegendData()
    result = asdict(data)
    assert result == {"gradients": [], "items": []}


def test_discrete_only():
    data = LegendData(items=[DiscreteEntry("Forest", "#006400")])
    result = asdict(data)
    assert len(result["items"]) == 1
    assert result["items"][0] == {"label": "Forest", "color": "#006400"}
    assert result["gradients"] == []


def test_gradient_only():
    data = LegendData(
        gradients=[GradientEntry(colors=["#ffff00", "#8b0000"], labels=["2001", "2024"])]
    )
    result = asdict(data)
    assert len(result["gradients"]) == 1
    assert result["gradients"][0]["colors"] == ["#ffff00", "#8b0000"]
    assert result["gradients"][0]["labels"] == ["2001", "2024"]
    assert result["gradients"][0]["title"] == ""


def test_mixed_legend():
    data = LegendData(
        gradients=[
            GradientEntry(
                colors=["#ffff00", "#8b0000"],
                labels=["2001", "2024"],
                title="Forest loss year",
            )
        ],
        items=[
            DiscreteEntry("Forest", "#006400"),
            DiscreteEntry("Non forest", "#d3d3d3"),
        ],
    )
    result = asdict(data)
    assert len(result["gradients"]) == 1
    assert result["gradients"][0]["title"] == "Forest loss year"
    assert len(result["items"]) == 2


def test_multi_stop_gradient():
    data = LegendData(
        gradients=[
            GradientEntry(
                colors=["#0000ff", "#00ff00", "#ff0000"],
                labels=["-1", "0", "1"],
                title="NDVI",
            )
        ],
    )
    result = asdict(data)
    assert len(result["gradients"][0]["colors"]) == 3
    assert len(result["gradients"][0]["labels"]) == 3
