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
    "You are JARVIS: a calm, precise, reliable personal assistant with a "
    "composed and subtly dry communication style. Answer as JARVIS, not as "
    "a generic Home Assistant assistant. Home Assistant is one integration "
    "and interface of JARVIS; it is not JARVIS' identity. When asked who you "
    "are, what you can do, or which abilities you have, answer from the "
    "perspective of JARVIS. Mention smart-home abilities when relevant, but "
    "also include JARVIS project capabilities when the user asks about "
    "JARVIS itself. Keep answers short, clear, source-backed when possible, "
    "and do not invent capabilities. "
    "Use list_capabilities for questions about what JARVIS can do or "
    "which Capability API functions are implemented. "
    "Always use list_extensions for questions containing or meaning "
    "Erweiterungen, Extensions, optionale Fähigkeiten, optional abilities, "
    "or optionale Fähigkeitserweiterungen. "
    "list_extensions lists only installed or currently available optional "
    "JARVIS extensions. "
    "Use list_project_modules for questions about modules, components, "
    "packages, architecture, technical project structure, or implementation "
    "overview only. list_project_modules is deprecated and legacy. Never use "
    "list_project_modules for Erweiterungen, Extensions, optionale "
    "Fähigkeiten, optional abilities, or extension questions. "
    "Use inspect_project_module for questions about one specific module, "
    "feature, or capability."
)


class JarvisLLMAPI(llm.API):
    """JARVIS LLM API boundary."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: JarvisAddonClient,
    ) -> None:
        super().__init__(hass=hass, id=API_ID, name=API_NAME)
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
                ListExtensionsTool(self._client),
                ListProjectModulesTool(self._client),
            ],
        )


class InspectProjectModuleTool(llm.Tool):
    """Tool for Project JARVIS module inspection."""

    name = "inspect_project_module"
    description = (
        "Use when the user asks about one specific Project JARVIS module, "
        "feature, or capability, for example whether the Windows Agent is "
        "implemented or what the Startup Report module is. Checks whether "
        "that single item is installed, planned, documented, historical, "
        "idea-only, or not found."
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


class ListProjectModulesTool(llm.Tool):
    """Legacy tool for listing technical Project JARVIS modules."""

    name = "list_project_modules"
    description = (
        "Deprecated legacy tool. Use only for technical Project JARVIS "
        "structure questions about modules, components, packages, architecture "
        "elements, project-structure items, or implementation units. Never use "
        "for Erweiterungen, Extensions, optionale Fähigkeiten, optional "
        "abilities, optionale Fähigkeitserweiterungen, or any extension "
        "question. For extension questions use list_extensions instead. For "
        "general ability questions use list_capabilities instead."
    )
    parameters = vol.Schema({})

    def __init__(self, client: JarvisAddonClient) -> None:
        self._client = client

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on list_project_modules capability."""
        return await self._client.execute_capability(
            capability="list_project_modules",
            parameters={},
        )


class ListExtensionsTool(llm.Tool):
    """Tool for listing installed optional JARVIS extensions."""

    name = "list_extensions"
    description = (
        "Use for any question about Erweiterungen, Extensions, optionale "
        "Fähigkeiten, optional abilities, or optionale Fähigkeitserweiterungen. "
        "Lists installed or currently available optional JARVIS extensions "
        "only. This is the correct tool for 'Welche Erweiterungen hast du?', "
        "'Welche Extensions sind installiert?', and 'Welche optionalen "
        "Fähigkeiten hast du?'. Do not use list_project_modules for these "
        "questions."
    )
    parameters = vol.Schema({})

    def __init__(self, client: JarvisAddonClient) -> None:
        self._client = client

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on list_extensions capability."""
        return await self._client.execute_capability(
            capability="list_extensions",
            parameters={},
        )


class ListCapabilitiesTool(llm.Tool):
    """Tool for listing implemented JARVIS capabilities."""

    name = "list_capabilities"
    description = (
        "Use when the user asks what JARVIS can do, which abilities it has, "
        "or which Capability API functions are currently implemented. This "
        "lists executable JARVIS capabilities, not architecture modules or "
        "project structure."
    )
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
        JarvisLLMAPI(hass, client),
    )
