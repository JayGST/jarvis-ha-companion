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
    "Use the user-facing taxonomy Capabilities, Extensions, Ideas, Roadmap, "
    "and Decisions. Do not present modules as a separate user-facing concept. "
    "Use list_capabilities for questions about what JARVIS can do, which "
    "abilities or capabilities it has, which Capability API functions are "
    "implemented, or user-facing module questions such as 'Welche Module "
    "hast du?' unless the user explicitly asks about implementation, code, "
    "repository layout, or architecture. "
    "Always use list_extensions for questions containing or meaning "
    "Erweiterungen, Extensions, optionale Fähigkeiten, optional abilities, "
    "or optionale Fähigkeitserweiterungen. list_extensions lists only "
    "installed or currently available optional JARVIS extensions. "
    "Use get_ideas for questions about ideas, Ideensammlung, documented ideas, "
    "future ideas, or uncommitted possibilities. Do NOT use get_ideas for "
    "implemented capabilities, installed extensions, roadmap items, or ADR "
    "decisions. get_ideas lists ideas only. "
    "Use get_roadmap_items for planned roadmap work. "
    "Use find_decision for accepted architecture decisions. "
    "Use inspect_project_module for questions about one specific project "
    "item, feature, or capability, and for explicit implementation, "
    "architecture, code structure, repository layout, or software "
    "architecture questions."
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
                GetIdeasTool(self._client),
            ],
        )


class InspectProjectModuleTool(llm.Tool):
    """Tool for specific Project JARVIS source inspection."""

    name = "inspect_project_module"
    description = (
        "Use when the user asks about one specific Project JARVIS item, "
        "feature, capability, implementation detail, architecture element, "
        "code structure, repository layout, or software architecture question. "
        "Examples: 'Ist der Windows Agent implementiert?' or 'Wie ist deine "
        "Architektur aufgebaut?'. Checks whether that single item is installed, "
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


class ListExtensionsTool(llm.Tool):
    """Tool for listing installed optional JARVIS extensions."""

    name = "list_extensions"
    description = (
        "Use for any question about Erweiterungen, Extensions, optionale "
        "Fähigkeiten, optional abilities, or optionale Fähigkeitserweiterungen. "
        "Lists installed or currently available optional JARVIS extensions "
        "only. This is the correct tool for 'Welche Erweiterungen hast du?', "
        "'Welche Extensions sind installiert?', and 'Welche optionalen "
        "Fähigkeiten hast du?'."
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


class GetIdeasTool(llm.Tool):
    """Tool for retrieving documented JARVIS ideas."""

    name = "get_ideas"
    description = (
        "Use for questions about ideas, Ideensammlung, documented ideas, "
        "future ideas, or uncommitted possibilities. Returns the documented "
        "JARVIS ideas only."
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
        """Call the JARVIS Add-on get_ideas capability."""
        return await self._client.execute_capability(
            capability="get_ideas",
            parameters={},
        )


class ListCapabilitiesTool(llm.Tool):
    """Tool for listing implemented JARVIS capabilities."""

    name = "list_capabilities"
    description = (
        "Use when the user asks what JARVIS can do, which abilities or "
        "capabilities it has, which Capability API functions are currently "
        "implemented, or user-facing module questions such as 'Welche Module "
        "hast du?'. This lists executable JARVIS capabilities. Do not use for "
        "explicit implementation, architecture, code, or repository layout "
        "questions; use inspect_project_module for those."
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
