"""Home Assistant LLM integration boundary for JARVIS."""

from __future__ import annotations

from collections.abc import Callable

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.util.json import JsonObjectType

from .const import DOMAIN

API_ID = f"{DOMAIN}.capabilities"
API_NAME = "JARVIS"
API_PROMPT = (
    "JARVIS exposes project-specific capabilities through tools. "
    "Use these tools when a user asks about Project JARVIS capabilities."
)


class JarvisLLMAPI(llm.API):
    """JARVIS LLM API boundary."""

    async def async_get_api_instance(
        self,
        llm_context: llm.LLMContext,
    ) -> llm.APIInstance:
        """Return the JARVIS LLM API instance."""
        return llm.APIInstance(
            api=self,
            api_prompt=API_PROMPT,
            llm_context=llm_context,
            tools=[InspectProjectModuleTool()],
        )


class InspectProjectModuleTool(llm.Tool):
    """Placeholder tool for Project JARVIS module inspection."""

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

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Return a placeholder result until Add-on execution is connected."""
        return {
            "message": (
                "JARVIS inspect_project_module tool is registered, "
                "but Add-on execution is not connected yet."
            ),
            "module_name": tool_input.tool_args["module_name"],
        }


def async_setup_llm_api(hass: HomeAssistant) -> Callable[[], None]:
    """Register the JARVIS LLM API with Home Assistant."""
    return llm.async_register_api(
        hass,
        JarvisLLMAPI(hass, API_ID, API_NAME),
    )
