"""Reactive state for the GEE Source app."""

import solara


class GeeSourceState:
    """Flat reactive state container for the GEE Source app.

    Attributes:
        app_url: The Earth Engine Apps URL the user wants to inspect.
        filename: The sanitized filename (without extension) used when saving.
        raw_code: The raw JavaScript source extracted from the app, if any.
        highlighted_html: Syntax-highlighted HTML for the extracted code.
        saved_path: Absolute path of the most recent save, if any.
    """

    def __init__(self):
        self.app_url = solara.reactive("")
        self.filename = solara.reactive("")
        self.raw_code = solara.reactive("")
        self.highlighted_html = solara.reactive("")
        self.saved_path = solara.reactive("")
