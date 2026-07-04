"""Home Assistant LLM integration boundary for JARVIS."""

from __future__ import annotations

from collections.abc import Callable

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.util.json import JsonObjectType

from .addon_client import JarvisAddonClient
from .const import DOMAIN

API_ID = f"{DOMAIN}.capabilities"
API_NAME = "JARVIS"
API_PROMPT = (
    "JARVIS exposes project-specific capabilities through tools. "
    "Use these tools when a user asks about Project JARVIS capabilities."
)


class JarvisLLMAPI(llm.API):
    """JARVIS LLM API boundary."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_id: str,
        name: str,
        client: JarvisAddonClient,
    ) -> None:
        super().__init__(hass, api_id, name)
        self._client = client

    async def async_get_api_instance(
        self,
        llm_context: llm.LLMContext,
    ) -> llm.APIInstance:
        """Return the JARVIS LLM API instance."""
        return llm.APIInstance(
            api=self,
            api_prompt=API_PROMPT,
            llm_context=llm_context,
            tools=[
                InspectProjectModuleTool(self._client),
                ListCapabilitiesTool(self._client),
            ],
        )


class InspectProjectModuleTool(llm.Tool):
    """Tool for Project JARVIS module inspection."""

    name = "inspect_project_module"
    description = (
        "Checks whether a Project JARVIS module or capability is installed, "
        "planned, documented, historical, idea-only, or not found."
    )
    parameters = vol.Schema(
        {
            vol.Required("module_name"): str,
        }
    )

    def __init__(self, client: JarvisAddonClient) -> None:
        self._client = client

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on inspect_project_module capability."""
        module_name = tool_input.tool_args["module_name"]

        return await self._client.execute_capability(
            capability="inspect_project_module",
            parameters={
                "module_name": module_name,
            },
        )


class ListCapabilitiesTool(llm.Tool):
    """Tool for listing implemented JARVIS capabilities."""

    name = "list_capabilities"
    description = "Lists currently implemented Project JARVIS capabilities."
    parameters = vol.Schema({})

    def __init__(self, client: JarvisAddonClient) -> None:
        self._client = client

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on list_capabilities capability."""
        return await self._client.execute_capability(
            capability="list_capabilities",
            parameters={},
        )


def async_setup_llm_api(
    hass: HomeAssistant,
    client: JarvisAddonClient,
) -> Callable[[], None]:
    """Register the JARVIS LLM API with Home Assistant."""
    return llm.async_register_api(
        hass,
        JarvisLLMAPI(hass, API_ID, API_NAME, client),
    )
