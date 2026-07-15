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
FALLBACK_IDENTITY_PROMPT = (
    "Runtime JARVIS identity is currently unavailable from Project-JARVIS. "
    "Do not invent identity, personality, or capability details."
)
COMPANION_TOOL_INSTRUCTIONS = (
    "The Home Assistant Companion is a thin adapter. Use its LLM tools to "
    "forward capability requests to Project-JARVIS. Do not treat the "
    "Companion as the source of JARVIS business logic, memory, project "
    "knowledge, finance, Windows, context, or personality behavior. Keep "
    "responses grounded in the runtime identity and tool results. Do not "
    "invent capabilities."
)
CAPABILITY_GUIDANCE = (
    "Use the user-facing taxonomy Capabilities, Extensions, Ideas, Roadmap, "
    "and Decisions. Do not present modules as a separate user-facing concept. "
    "Use list_capabilities for questions about what JARVIS can do, which "
    "abilities or capabilities it has, which Capability API functions are "
    "implemented, or user-facing module questions such as 'Welche Module "
    "hast du?' unless the user explicitly asks about implementation, code, "
    "repository layout, or architecture. "
    "Always use list_extensions for questions containing or meaning "
    "Erweiterungen, Extensions, optionale Faehigkeiten, optional abilities, "
    "or optionale Faehigkeitserweiterungen. list_extensions lists only "
    "installed or currently available optional JARVIS extensions. "
    "Use get_ideas for questions about ideas, Ideensammlung, documented ideas, "
    "future ideas, or uncommitted possibilities. Do not use get_ideas for "
    "implemented capabilities, installed extensions, roadmap items, or ADR "
    "decisions. get_ideas lists ideas only. "
    "Use get_roadmap_items for direct requests to list planned roadmap work. "
    "Use find_decision for direct requests about accepted architecture "
    "decisions or ADRs. "
    "For almost every broad question about JARVIS architecture, roadmap, "
    "development, project decisions, open items, engineering discussions, "
    "implementation history, or project documentation, first consider "
    "search_project. Specialized tools such as find_decision, "
    "inspect_project_module, get_roadmap_items, get_runtime_info, and "
    "get_runtime_capabilities remain better when the user clearly asks for "
    "that exact structured information. Do not use search_project for "
    "general knowledge, internet search, Windows filesystem search, or Home "
    "Assistant entity queries. Avoid repeated search_project calls. If the "
    "first search gives enough information, answer directly. If refinement "
    "is needed, perform at most one additional focused search. Avoid chains "
    "of three or more speculative searches. Summarize search results "
    "naturally unless the user explicitly asks for raw results. Prefer "
    "wording such as 'The project documentation describes...', 'The current "
    "roadmap plans...', or 'The engineering notes indicate...'. Do not say "
    "'I searched ROADMAP.md' or 'I searched OPEN_ITEMS.md' unless the user "
    "explicitly asks where the information came from. "
    "Use get_runtime_status for current reachability questions such as "
    "whether the Windows Agent is reachable or online, whether the main PC "
    "is on, whether the desktop runtime is running, or whether JARVIS can "
    "currently reach the PC. Status questions require a fresh tool call. A "
    "reachable Windows Agent means the Windows PC is currently running. The "
    "result only proves current reachability and reported health status; it "
    "does not prove long-term stability, screen state, user presence, lock "
    "state, workload, or standby details. Do not claim the agent is stable "
    "unless the tool result provides monitoring data that supports that. "
    "Use get_runtime_info when the user asks for Windows Agent information, "
    "hostname, operating system, platform, architecture, or Python runtime "
    "information. Use get_runtime_capabilities when the user asks what the "
    "Windows Agent can do, which capabilities it exposes, or which Windows "
    "Agent functions are available. "
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
        identity_prompt: str | None,
    ) -> None:
        super().__init__(hass=hass, id=API_ID, name=API_NAME)
        self._client = client
        self._api_prompt = build_api_prompt(identity_prompt)

    async def async_get_api_instance(
        self,
        llm_context: llm.LLMContext,
    ) -> llm.APIInstance:
        """Return the JARVIS LLM API instance."""
        return llm.APIInstance(
            api=self,
            api_prompt=self._api_prompt,
            llm_context=llm_context,
            tools=[
                InspectProjectModuleTool(self._client),
                ListCapabilitiesTool(self._client),
                ListExtensionsTool(self._client),
                GetIdeasTool(self._client),
                GetRoadmapItemsTool(self._client),
                FindDecisionTool(self._client),
                SearchProjectTool(self._client),
                GetRuntimeStatusTool(self._client),
                GetRuntimeInfoTool(self._client),
                GetRuntimeCapabilitiesTool(self._client),
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
        "Faehigkeiten, optional abilities, or optionale Faehigkeitserweiterungen. "
        "Lists installed or currently available optional JARVIS extensions "
        "only. This is the correct tool for 'Welche Erweiterungen hast du?', "
        "'Welche Extensions sind installiert?', and 'Welche optionalen "
        "Faehigkeiten hast du?'."
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


class GetRoadmapItemsTool(llm.Tool):
    """Tool for retrieving documented JARVIS roadmap items."""

    name = "get_roadmap_items"
    description = (
        "Use for questions about planned roadmap work, roadmap items, "
        "upcoming work, or planned features. Returns the documented JARVIS "
        "roadmap items only."
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
        """Call the JARVIS Add-on get_roadmap_items capability."""
        return await self._client.execute_capability(
            capability="get_roadmap_items",
            parameters={},
        )


class FindDecisionTool(llm.Tool):
    """Tool for retrieving accepted JARVIS architecture decisions."""

    name = "find_decision"
    description = (
        "Use for questions about accepted architecture decisions, ADRs, or "
        "documented design decisions. Returns the relevant JARVIS decision "
        "record(s)."
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
        """Call the JARVIS Add-on find_decision capability."""
        return await self._client.execute_capability(
            capability="find_decision",
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


class SearchProjectTool(llm.Tool):
    """Tool for searching Project JARVIS knowledge through the Add-on."""

    name = "search_project"
    description = (
        "Best first tool for broad Project JARVIS questions about "
        "architecture, roadmap, development, project decisions, open items, "
        "engineering discussions, implementation history, or project "
        "documentation. Do not use for general knowledge, internet search, "
        "Windows filesystem search, or Home Assistant entity queries. Use "
        "specialized tools instead when the user clearly asks for one "
        "specific ADR decision, one specific implementation item, direct "
        "roadmap listing, or Windows runtime status. Avoid repeated search "
        "calls; one focused refinement search is enough when needed."
    )
    parameters = vol.Schema(
        {
            vol.Required("query"): str,
            vol.Optional("limit"): int,
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
        """Call the JARVIS Add-on search_project capability."""
        parameters: dict[str, str | int] = {
            "query": tool_input.tool_args["query"],
        }

        if "limit" in tool_input.tool_args:
            parameters["limit"] = tool_input.tool_args["limit"]

        return await self._client.execute_capability(
            capability="search_project",
            parameters=parameters,
        )


class GetRuntimeStatusTool(llm.Tool):
    """Tool for checking whether the desktop runtime is reachable."""

    name = "get_runtime_status"
    description = (
        "Use for current status questions: whether the Windows Agent is "
        "reachable or online, whether the user's main PC is on, whether the "
        "desktop runtime is running, or whether JARVIS can currently reach "
        "the PC. Always make a fresh tool call for current status. A "
        "reachable Windows Agent means the Windows PC is currently running. "
        "The result only proves current reachability and reported health "
        "status; it does not prove long-term stability, screen state, user "
        "presence, lock state, workload, or standby details. This is "
        "read-only."
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
        """Call the JARVIS Add-on runtime health capability."""
        return await self._client.execute_capability(
            capability="system.health",
            parameters={},
        )


class GetRuntimeInfoTool(llm.Tool):
    """Tool for retrieving desktop runtime information."""

    name = "get_runtime_info"
    description = (
        "Use when the user asks for Windows Agent information, hostname, "
        "operating system, platform, architecture, or Python runtime "
        "information. This is read-only."
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
        """Call the JARVIS Add-on runtime information capability."""
        return await self._client.execute_capability(
            capability="system.info",
            parameters={},
        )


class GetRuntimeCapabilitiesTool(llm.Tool):
    """Tool for listing desktop runtime capabilities."""

    name = "get_runtime_capabilities"
    description = (
        "Use when the user asks what the Windows Agent can do, which "
        "capabilities the Windows Agent exposes, or which Windows Agent "
        "functions are available. This is read-only."
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
        """Call the JARVIS Add-on runtime capabilities capability."""
        return await self._client.execute_capability(
            capability="system.capabilities",
            parameters={},
        )


def async_setup_llm_api(
    hass: HomeAssistant,
    client: JarvisAddonClient,
    identity_prompt: str | None,
) -> Callable[[], None]:
    """Register the JARVIS LLM API with Home Assistant."""
    return llm.async_register_api(
        hass,
        JarvisLLMAPI(hass, client, identity_prompt),
    )


def build_api_prompt(identity_prompt: str | None) -> str:
    """Build the LLM API prompt in the documented order."""
    runtime_identity = (
        identity_prompt.strip()
        if identity_prompt is not None and identity_prompt.strip()
        else FALLBACK_IDENTITY_PROMPT
    )

    return "\n\n".join(
        (
            runtime_identity,
            COMPANION_TOOL_INSTRUCTIONS,
            CAPABILITY_GUIDANCE,
        )
    )
