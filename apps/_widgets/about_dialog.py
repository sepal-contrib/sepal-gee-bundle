"""One-time About dialog backed by browser localStorage.

Auto-opens the dialog on first visit and writes a `1` flag to
localStorage when the user dismisses it. Subsequent visits read the
flag back and skip the auto-open. Each app passes its own
`storage_key` so the flag is scoped per app.
"""

from typing import Optional

import reacton.ipyvuetify as rv
import solara

from .local_storage import LocalStorageBridge

_DISMISSED = "1"
_DEFAULT_MARKDOWN_STYLE = (
    "img { width: 70%; display: block; margin: 16px auto 0; border-radius: 8px; }"
)


@solara.component
def AboutOnceDialog(
    storage_key: str,
    title: str,
    markdown_text: str,
    max_width: int = 1100,
    markdown_style: Optional[str] = None,
):
    """Show the About modal until the user dismisses it once."""
    bridge = solara.use_memo(
        lambda: LocalStorageBridge(storage_key=storage_key),
        [storage_key],
    )

    loaded = solara.use_reactive(bool(bridge.loaded))
    value = solara.use_reactive(bridge.value or "")

    def _attach():
        def _on_loaded(change):
            loaded.set(bool(change["new"]))

        def _on_value(change):
            value.set(change["new"] or "")

        bridge.observe(_on_loaded, "loaded")
        bridge.observe(_on_value, "value")
        loaded.set(bool(bridge.loaded))
        value.set(bridge.value or "")

        def _detach():
            bridge.unobserve(_on_loaded, "loaded")
            bridge.unobserve(_on_value, "value")

        return _detach

    solara.use_effect(_attach, [bridge])

    show = loaded.value and value.value != _DISMISSED

    def _dismiss():
        if bridge.value != _DISMISSED:
            bridge.value = _DISMISSED

    def _on_v_model(new_value: bool):
        if not new_value:
            _dismiss()

    rv.Html(tag="div", children=[bridge], style_="display:none;")

    with rv.Dialog(
        v_model=show,
        on_v_model=_on_v_model,
        max_width=str(max_width),
        scrollable=True,
    ):
        with rv.Card():
            with rv.CardTitle(class_="d-flex align-center py-3 px-4"):
                rv.Icon(color="primary", class_="mr-2", children=["mdi-information-outline"])
                rv.Html(tag="span", class_="text-h6", children=[title])
                rv.Spacer()
                solara.Button(
                    icon_name="mdi-close",
                    icon=True,
                    on_click=_dismiss,
                )
            rv.Divider()
            with rv.CardText(class_="pa-4"):
                solara.Markdown(
                    markdown_text,
                    style=markdown_style or _DEFAULT_MARKDOWN_STYLE,
                )
