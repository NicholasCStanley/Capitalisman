"""Session-scoped settings override system.

Allows the UI to temporarily override config values (indicator weights,
thresholds) without modifying the on-disk settings.  When running outside
Streamlit (e.g. in tests), overrides are silently ignored and the default
values from config.settings are returned.
"""

from config import settings


def _session_key(name: str) -> str:
    return f"setting_override_{name}"


def get_setting(name: str):
    """Return the current effective value for *name*.

    Checks st.session_state for an override first; falls back to the
    corresponding attribute in config.settings.
    """
    try:
        import streamlit as st

        key = _session_key(name)
        if key in st.session_state:
            return st.session_state[key]
    except Exception:
        pass
    return getattr(settings, name)


def set_override(name: str, value) -> None:
    """Store an override in session state."""
    import streamlit as st

    st.session_state[_session_key(name)] = value


def clear_overrides() -> None:
    """Remove all setting overrides from session state."""
    try:
        import streamlit as st

        keys = [k for k in st.session_state if k.startswith("setting_override_")]
        for k in keys:
            del st.session_state[k]
    except Exception:
        pass
