"""Bridge a value in the browser's localStorage to a Python traitlet.

Mount the widget inside any rendered Solara/ipyvuetify tree (e.g. wrapped
in a `display:none` div). On mount it reads `localStorage[storage_key]`
into `value` and sets `loaded=True`. Subsequent writes to `value` from
Python are mirrored back into `localStorage`.
"""

import ipyvuetify as v
from traitlets import Bool, Unicode

_BRIDGE_TEMPLATE = """
<script class='sepal-localstorage-bridge'>
{
    mounted() {
        let stored = "";
        try {
            stored = localStorage.getItem(this.storage_key) || "";
        } catch (e) {}
        this.value = stored;
        this.loaded = true;
    },
    watch: {
        value(newVal) {
            try {
                const cur = localStorage.getItem(this.storage_key) || "";
                const next = newVal == null ? "" : String(newVal);
                if (cur !== next) {
                    localStorage.setItem(this.storage_key, next);
                }
            } catch (e) {}
        }
    }
}
</script>
"""


class LocalStorageBridge(v.VuetifyTemplate):
    """Sync a single localStorage entry with a Python traitlet."""

    storage_key = Unicode("").tag(sync=True)
    value = Unicode("", allow_none=True).tag(sync=True)
    loaded = Bool(False).tag(sync=True)
    template = Unicode(_BRIDGE_TEMPLATE).tag(sync=True)
