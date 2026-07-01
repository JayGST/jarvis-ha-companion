"""JARVIS Home Assistant companion integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .llm import async_setup_llm_api


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up the JARVIS Home Assistant companion integration from a config entry."""
    unregister = async_setup_llm_api(hass)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "unregister_llm_api": unregister,
    }

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload the JARVIS Home Assistant companion integration."""
    entry_data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    if entry_data is not None:
        unregister = entry_data.get("unregister_llm_api")

        if unregister is not None:
            unregister()

    if not hass.data.get(DOMAIN):
        hass.data.pop(DOMAIN, None)

    return True
