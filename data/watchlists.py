"""Persistent watchlist storage (JSON file in ~/.capitalisman/)."""

import json
from pathlib import Path

_WATCHLIST_DIR = Path.home() / ".capitalisman"
_WATCHLIST_FILE = _WATCHLIST_DIR / "watchlists.json"


def _ensure_dir() -> None:
    _WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)


def load_watchlists() -> dict[str, list[str]]:
    """Load all user watchlists from disk.

    Returns:
        dict mapping watchlist name to list of ticker strings.
    """
    if not _WATCHLIST_FILE.exists():
        return {}
    try:
        data = json.loads(_WATCHLIST_FILE.read_text())
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if isinstance(v, list)}
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def save_watchlist(name: str, tickers: list[str]) -> None:
    """Save or update a watchlist."""
    _ensure_dir()
    watchlists = load_watchlists()
    watchlists[name] = tickers
    _WATCHLIST_FILE.write_text(json.dumps(watchlists, indent=2))


def delete_watchlist(name: str) -> bool:
    """Delete a watchlist by name. Returns True if it existed."""
    watchlists = load_watchlists()
    if name not in watchlists:
        return False
    del watchlists[name]
    _ensure_dir()
    _WATCHLIST_FILE.write_text(json.dumps(watchlists, indent=2))
    return True
