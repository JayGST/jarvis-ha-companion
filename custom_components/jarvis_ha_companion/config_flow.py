"""Config flow for the JARVIS Home Assistant companion integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries

from .const import CONF_BASE_URL, DOMAIN

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL): vol.All(str, vol.Length(min=1)),
    }
)


class JarvisHACompanionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the JARVIS Home Assistant companion integration."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Create the JARVIS Home Assistant companion config entry."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            base_url = user_input[CONF_BASE_URL].strip()

            return self.async_create_entry(
                title="JARVIS",
                data={
                    CONF_BASE_URL: base_url,
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
        )
