"""Tests for config-entry setup and config flow behavior."""

from __future__ import annotations

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm

from custom_components.jarvis_ha_companion import async_setup_entry
from custom_components.jarvis_ha_companion.addon_client import (
    IdentityPrompt,
    JarvisAddonClientError,
)
from custom_components.jarvis_ha_companion.config_flow import (
    JarvisHACompanionConfigFlow,
)
from custom_components.jarvis_ha_companion.const import CONF_BASE_URL, DOMAIN
from custom_components.jarvis_ha_companion.llm import FALLBACK_IDENTITY_PROMPT


class IdentityClient:
    def __init__(self, hass: HomeAssistant, base_url: str) -> None:
        self.base_url = base_url
        self.identity_calls = 0
        self.execute_calls: list[tuple[str, dict[str, object]]] = []

    async def get_identity_prompt(self) -> IdentityPrompt:
        self.identity_calls += 1
        return IdentityPrompt(
            prompt="Canonical runtime identity.",
            source="docs/identity/JARVIS_IDENTITY.md",
            content_sha256="abc123",
        )

    async def execute_capability(
        self,
        *,
        capability: str,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        self.execute_calls.append((capability, parameters))
        return {"result": {}}


class FailingIdentityClient(IdentityClient):
    async def get_identity_prompt(self) -> IdentityPrompt:
        self.identity_calls += 1
        raise JarvisAddonClientError("identity unavailable")


@pytest.mark.asyncio
async def test_setup_fetches_identity_once_and_reuses_cached_prompt(monkeypatch) -> None:
    """Setup loads identity once; API instances do not refetch per message."""
    import custom_components.jarvis_ha_companion as integration

    monkeypatch.setattr(integration, "JarvisAddonClient", IdentityClient)
    hass = HomeAssistant()
    entry = ConfigEntry(data={CONF_BASE_URL: "http://jarvis.local"})

    assert await async_setup_entry(hass, entry) is True

    client = hass.data[DOMAIN][entry.entry_id]["client"]
    api = hass.data["_registered_apis"][0]
    first = await api.async_get_api_instance(llm.LLMContext())
    second = await api.async_get_api_instance(llm.LLMContext())

    assert client.identity_calls == 1
    assert first.api_prompt == second.api_prompt
    assert first.api_prompt.startswith("Canonical runtime identity.")


@pytest.mark.asyncio
async def test_setup_uses_fallback_when_identity_unavailable(monkeypatch, caplog) -> None:
    """Identity failures do not prevent integration setup."""
    import custom_components.jarvis_ha_companion as integration

    monkeypatch.setattr(integration, "JarvisAddonClient", FailingIdentityClient)
    hass = HomeAssistant()
    entry = ConfigEntry(data={CONF_BASE_URL: "http://jarvis.local"})

    assert await async_setup_entry(hass, entry) is True

    client = hass.data[DOMAIN][entry.entry_id]["client"]
    api = hass.data["_registered_apis"][0]
    instance = await api.async_get_api_instance(llm.LLMContext())

    assert client.identity_calls == 1
    assert instance.api_prompt.startswith(FALLBACK_IDENTITY_PROMPT)
    assert "Unable to load runtime JARVIS identity" in caplog.text


@pytest.mark.asyncio
async def test_config_flow_still_creates_trimmed_base_url_entry() -> None:
    """Existing config-flow behavior remains intact."""
    flow = JarvisHACompanionConfigFlow()

    result = await flow.async_step_user(
        {
            CONF_BASE_URL: "  http://jarvis.local  ",
        }
    )

    assert result == {
        "type": "create_entry",
        "title": "JARVIS",
        "data": {
            CONF_BASE_URL: "http://jarvis.local",
        },
    }
