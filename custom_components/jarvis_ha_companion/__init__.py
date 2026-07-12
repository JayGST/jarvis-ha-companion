"""JARVIS Home Assistant companion integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .addon_client import JarvisAddonClient, JarvisAddonClientError
from .const import CONF_BASE_URL, DOMAIN
from .llm import async_setup_llm_api

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up the JARVIS Home Assistant companion integration from a config entry."""
    client = JarvisAddonClient(
        hass=hass,
        base_url=entry.data[CONF_BASE_URL],
    )

    identity_prompt = None

    try:
        identity = await client.get_identity_prompt()
        identity_prompt = identity.prompt
    except JarvisAddonClientError as error:
        _LOGGER.warning(
            "Unable to load runtime JARVIS identity from Project-JARVIS; "
            "using neutral companion fallback prompt: %s",
            error,
        )

    unregister = async_setup_llm_api(hass, client, identity_prompt)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "identity_prompt": identity_prompt,
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
