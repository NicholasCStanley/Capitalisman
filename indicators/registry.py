"""Indicator registry with auto-registration decorator."""

from indicators.base import BaseIndicator

_registry: dict[str, type[BaseIndicator]] = {}


def register(cls: type[BaseIndicator]) -> type[BaseIndicator]:
    """Class decorator to register an indicator."""
    instance = cls()
    _registry[instance.name] = cls
    return cls


def get_all_indicators() -> dict[str, BaseIndicator]:
    """Return instances of all registered indicators."""
    return {name: cls() for name, cls in _registry.items()}


def get_indicator(name: str) -> BaseIndicator:
    """Get a single indicator instance by name."""
    if name not in _registry:
        raise KeyError(f"Unknown indicator: {name}")
    return _registry[name]()


def get_indicators_by_category(category: str) -> dict[str, BaseIndicator]:
    """Return all indicators in a given category."""
    result = {}
    for name, cls in _registry.items():
        inst = cls()
        if inst.category == category:
            result[name] = inst
    return result


def list_indicator_names() -> list[str]:
    """Return sorted list of all registered indicator names."""
    return sorted(_registry.keys())
