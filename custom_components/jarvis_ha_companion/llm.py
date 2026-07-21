"""Home Assistant LLM integration boundary for JARVIS."""

from __future__ import annotations

from collections.abc import Callable

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.util.json import JsonObjectType

from .activation import ActivationRegistry, ActivationWorkflow
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
    "get_runtime_capabilities, and get_system_metrics remain better when "
    "the user clearly asks for "
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
    "Use repository_file_exists, list_repository_directory, and "
    "read_repository_file only for live files inside explicitly approved "
    "Windows Agent repositories. Use search_project for synchronized "
    "Project Knowledge and do not use repository filesystem tools for "
    "general project questions when search_project is sufficient. Do not "
    "claim access to arbitrary Desktop, Documents, drive, or system folder "
    "locations. Do not invent repository IDs; ask for the approved "
    "repository ID or relative path when genuinely missing. Absolute paths "
    "and parent-directory traversal are unavailable. Repository filesystem "
    "tools are read-only; write, delete, move, and rename operations are "
    "unavailable. "
    "Use get_runtime_status for current reachability questions such as "
    "whether the Windows Agent is reachable or online, whether the main PC "
    "is on, whether the desktop runtime is running, or whether JARVIS can "
    "currently reach the PC. Status questions require a fresh tool call. A "
    "reachable Windows Agent means the Windows PC is currently running. The "
    "result only proves current reachability and reported health status; it "
    "does not prove long-term stability, screen state, user presence, lock "
    "state, workload, or standby details. Do not claim the agent is stable "
    "unless the tool result provides monitoring data that supports that. "
    "Prefer wording such as 'The Windows Agent is currently reachable and "
    "reports status ok.' when system.health returns status ok. "
    "Use get_runtime_info when the user asks for Windows Agent information, "
    "hostname, operating system, platform, architecture, or Python runtime "
    "information. Use get_runtime_capabilities when the user asks what the "
    "Windows Agent can do, which capabilities it exposes, or which Windows "
    "Agent functions are available. "
    "Use get_system_metrics for questions about current Windows PC metrics "
    "such as CPU usage, CPU temperature, GPU usage, GPU temperature, RAM "
    "usage, drive usage, free disk space, uptime, network totals, or overall "
    "current PC status. get_runtime_status checks current reachability and "
    "reported health; get_system_metrics retrieves current system "
    "measurements. Do not use get_system_metrics for project documentation, "
    "historical trends, Home Assistant entity values, process lists, "
    "services, files, Git, or long-term stability claims. The tool returns "
    "one complete live snapshot, but answer only with metrics relevant to "
    "the user's question. Do not dump the raw complete result unless the "
    "user explicitly asks for all raw metrics. Nullable or missing metric "
    "values mean unavailable, not zero; do not infer values, and do not "
    "describe unavailable sensors as errors when the capability call itself "
    "succeeded. Metrics alone do not prove long-term stability, absence of "
    "problems, screen state, user presence, standby state, or future "
    "performance. "
    "When answering capability questions, distinguish three layers clearly. "
    "Windows Agent capabilities are operations implemented and advertised by "
    "the Windows Agent; discovering them does not grant permission and does "
    "not mean Claude can call them. Project-JARVIS routed capabilities are "
    "capabilities explicitly owned and routed by Project-JARVIS, still "
    "subject to authorization and policy. Companion tools are the only "
    "operations Claude can directly invoke through the current Home Assistant "
    "integration, and they use fixed allowlisted mappings only. If asked what "
    "the Windows Agent can do, summarize the Agent's implemented capability "
    "inventory from get_runtime_capabilities, then separately state which "
    "operations are directly exposed through Companion tools. Use wording "
    "such as 'The Windows Agent implements these capabilities. Through the "
    "current Home Assistant Companion, I can directly use only the explicitly "
    "exposed tools.' The currently exposed categories are runtime status, "
    "runtime information, runtime capability discovery, live system metrics, "
    "deterministic Project Search, approved repository file existence checks, "
    "approved repository directory listing, approved small UTF-8 repository "
    "file reads, approved application launch for Visual Studio, and approved "
    "device wake for the registered Gaming-PC. Do "
    "not describe write, Git, Task Scope, audit, or other discovered Windows "
    "Agent capabilities as directly callable unless a dedicated Companion "
    "tool exists. "
    "Use control_device_power when the user explicitly asks to wake, start, "
    "turn on, einschalten, starten, wecken, or mach an the registered "
    "Gaming-PC or main PC. The only supported device_id is gaming_pc and the "
    "only supported action is wake. Success means the Wake-on-LAN request was "
    "sent through Project-JARVIS and Home Assistant; it does not prove the PC "
    "booted, became ready, or that the Windows Agent is reachable. Do not use "
    "this tool for shutdown, restart, sleep, hibernate, scripts, entities, or "
    "arbitrary Home Assistant service calls. "
    "Use launch_application when the user explicitly asks to open, start, "
    "launch, or mach Visual Studio, Notepad, Chrome, Discord, Steam, "
    "Obsidian, or the Windows Editor auf. The supported application_id "
    "values are visual_studio, notepad, chrome, discord, steam and "
    "obsidian. Do not "
    "treat 'VS' as sufficient because it may mean "
    "Visual Studio Code; ask a brief clarification when ambiguous. Do not "
    "claim support for Visual Studio Code. Do not accept or mention paths, "
    "arguments, working directories, environment variables, discovery "
    "settings, or local overrides. "
    "When a tool response says activation is pending, waiting, retryable, "
    "cancelled, failed, or completed, treat activation_id as the handle for "
    "that exact request. Never ask the user to repeat repository IDs, file "
    "paths, metrics requests, or other capability arguments after activation "
    "has started; Project-JARVIS stores the original request server-side. If "
    "a response asks 'This requires waking your PC. Should I continue?', ask "
    "that confirmation plainly. To continue a pending activation use "
    "confirm_activation with the specific activation_id. To retry a "
    "retry-waiting activation use retry_activation. If the user says no, "
    "cancel, never mind, or stop, use cancel_activation. If multiple "
    "activations are waiting for confirmation, ask which one by summary; do "
    "not assume the latest. For natural follow-up questions such as 'Is it "
    "ready?', 'Is everything finished?', 'Continue', 'How far are you?', or "
    "'Cancel it', use the activation tools without exposing activation IDs "
    "to the user. Home Assistant conversations are request/response; do not "
    "claim that the Companion can speak later without another user message. "
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
        activation_workflow: ActivationWorkflow | None = None,
    ) -> None:
        super().__init__(hass=hass, id=API_ID, name=API_NAME)
        self._client = client
        self._activation_workflow = activation_workflow or ActivationWorkflow(
            client=client,
            registry=ActivationRegistry(),
        )
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
                InspectProjectModuleTool(self._client, self._activation_workflow),
                ListCapabilitiesTool(self._client, self._activation_workflow),
                ListExtensionsTool(self._client, self._activation_workflow),
                GetIdeasTool(self._client, self._activation_workflow),
                GetRoadmapItemsTool(self._client, self._activation_workflow),
                FindDecisionTool(self._client, self._activation_workflow),
                SearchProjectTool(self._client, self._activation_workflow),
                RepositoryFileExistsTool(self._client, self._activation_workflow),
                ListRepositoryDirectoryTool(self._client, self._activation_workflow),
                ReadRepositoryFileTool(self._client, self._activation_workflow),
                GetRuntimeStatusTool(self._client, self._activation_workflow),
                GetRuntimeInfoTool(self._client, self._activation_workflow),
                GetRuntimeCapabilitiesTool(self._client, self._activation_workflow),
                GetSystemMetricsTool(self._client, self._activation_workflow),
                LaunchApplicationTool(self._client, self._activation_workflow),
                ControlDevicePowerTool(self._client, self._activation_workflow),
                GetActivationStatusTool(self._activation_workflow),
                ConfirmActivationTool(self._activation_workflow),
                RetryActivationTool(self._activation_workflow),
                CancelActivationTool(self._activation_workflow),
            ],
        )


class JarvisCapabilityTool(llm.Tool):
    """Base class for fixed Project-JARVIS capability tools."""

    def __init__(
        self,
        client: JarvisAddonClient,
        activation_workflow: ActivationWorkflow | None = None,
    ) -> None:
        self._client = client
        self._activation_workflow = activation_workflow

    async def _execute_capability(
        self,
        *,
        capability: str,
        parameters: dict[str, object],
        llm_context: llm.LLMContext,
        summary: str,
    ) -> JsonObjectType:
        response = await self._client.execute_capability(
            capability=capability,
            parameters=parameters,
        )

        if self._activation_workflow is None:
            return response

        return await self._activation_workflow.observe_capability_response(
            response,
            conversation_context_id=_conversation_context_id(llm_context),
            capability_name=capability,
            user_facing_summary=summary,
        )


class InspectProjectModuleTool(JarvisCapabilityTool):
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

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on inspect_project_module capability."""
        module_name = tool_input.tool_args["module_name"]

        return await self._execute_capability(
            capability="inspect_project_module",
            parameters={
                "module_name": module_name,
            },
            llm_context=llm_context,
            summary=f"Inspect Project JARVIS item: {module_name}",
        )


class ListExtensionsTool(JarvisCapabilityTool):
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

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on list_extensions capability."""
        return await self._execute_capability(
            capability="list_extensions",
            parameters={},
            llm_context=llm_context,
            summary="List JARVIS extensions",
        )


class GetIdeasTool(JarvisCapabilityTool):
    """Tool for retrieving documented JARVIS ideas."""

    name = "get_ideas"
    description = (
        "Use for questions about ideas, Ideensammlung, documented ideas, "
        "future ideas, or uncommitted possibilities. Returns the documented "
        "JARVIS ideas only."
    )
    parameters = vol.Schema({})

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on get_ideas capability."""
        return await self._execute_capability(
            capability="get_ideas",
            parameters={},
            llm_context=llm_context,
            summary="Get JARVIS ideas",
        )


class GetRoadmapItemsTool(JarvisCapabilityTool):
    """Tool for retrieving documented JARVIS roadmap items."""

    name = "get_roadmap_items"
    description = (
        "Use for questions about planned roadmap work, roadmap items, "
        "upcoming work, or planned features. Returns the documented JARVIS "
        "roadmap items only."
    )
    parameters = vol.Schema({})

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on get_roadmap_items capability."""
        return await self._execute_capability(
            capability="get_roadmap_items",
            parameters={},
            llm_context=llm_context,
            summary="Get JARVIS roadmap items",
        )


class FindDecisionTool(JarvisCapabilityTool):
    """Tool for retrieving accepted JARVIS architecture decisions."""

    name = "find_decision"
    description = (
        "Use for questions about accepted architecture decisions, ADRs, or "
        "documented design decisions. Returns the relevant JARVIS decision "
        "record(s)."
    )
    parameters = vol.Schema({})

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on find_decision capability."""
        return await self._execute_capability(
            capability="find_decision",
            parameters={},
            llm_context=llm_context,
            summary="Find JARVIS architecture decision",
        )


class ListCapabilitiesTool(JarvisCapabilityTool):
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

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on list_capabilities capability."""
        return await self._execute_capability(
            capability="list_capabilities",
            parameters={},
            llm_context=llm_context,
            summary="List JARVIS capabilities",
        )


class SearchProjectTool(JarvisCapabilityTool):
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

        return await self._execute_capability(
            capability="search_project",
            parameters=parameters,
            llm_context=llm_context,
            summary=f"Search Project Knowledge for: {tool_input.tool_args['query']}",
        )


class RepositoryFileExistsTool(JarvisCapabilityTool):
    """Tool for checking an approved repository-relative file path."""

    name = "repository_file_exists"
    description = (
        "Use to check whether a file exists inside a Windows Agent repository "
        "that is explicitly approved in Project-JARVIS configuration. "
        "repository_id must name an approved repository. relative_path must "
        "be relative to that repository. Absolute paths and '..' traversal "
        "are not accepted. This tool cannot access arbitrary PC locations. "
        "Write, delete, move, and rename operations are unavailable."
    )
    parameters = vol.Schema(
        {
            vol.Required("repository_id"): vol.All(str, vol.Length(min=1)),
            vol.Required("relative_path"): vol.All(str, vol.Length(min=1)),
        }
    )

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on filesystem.file_exists capability."""
        return await self._execute_capability(
            capability="filesystem.file_exists",
            parameters={
                "repository_id": tool_input.tool_args["repository_id"],
                "relative_path": tool_input.tool_args["relative_path"],
            },
            llm_context=llm_context,
            summary=(
                "Check file exists: "
                f"{tool_input.tool_args['repository_id']}/"
                f"{tool_input.tool_args['relative_path']}"
            ),
        )


class ListRepositoryDirectoryTool(JarvisCapabilityTool):
    """Tool for listing an approved repository-relative directory path."""

    name = "list_repository_directory"
    description = (
        "Use to list a directory inside a Windows Agent repository that is "
        "explicitly approved in Project-JARVIS configuration. repository_id "
        "must name an approved repository. relative_path must be relative to "
        "that repository. Absolute paths and '..' traversal are not accepted. "
        "This tool cannot access arbitrary PC locations. Write, delete, move, "
        "and rename operations are unavailable."
    )
    parameters = vol.Schema(
        {
            vol.Required("repository_id"): vol.All(str, vol.Length(min=1)),
            vol.Required("relative_path"): vol.All(str, vol.Length(min=1)),
        }
    )

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on filesystem.list_directory capability."""
        return await self._execute_capability(
            capability="filesystem.list_directory",
            parameters={
                "repository_id": tool_input.tool_args["repository_id"],
                "relative_path": tool_input.tool_args["relative_path"],
            },
            llm_context=llm_context,
            summary=(
                "List directory: "
                f"{tool_input.tool_args['repository_id']}/"
                f"{tool_input.tool_args['relative_path']}"
            ),
        )


class ReadRepositoryFileTool(JarvisCapabilityTool):
    """Tool for reading an approved repository-relative UTF-8 text file."""

    name = "read_repository_file"
    description = (
        "Use to read a small UTF-8 text file inside a Windows Agent "
        "repository that is explicitly approved in Project-JARVIS "
        "configuration. repository_id must name an approved repository. "
        "relative_path must be relative to that repository. Absolute paths "
        "and '..' traversal are not accepted. This tool cannot access "
        "arbitrary PC locations. Write, delete, move, and rename operations "
        "are unavailable."
    )
    parameters = vol.Schema(
        {
            vol.Required("repository_id"): vol.All(str, vol.Length(min=1)),
            vol.Required("relative_path"): vol.All(str, vol.Length(min=1)),
        }
    )

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on filesystem.read_file capability."""
        return await self._execute_capability(
            capability="filesystem.read_file",
            parameters={
                "repository_id": tool_input.tool_args["repository_id"],
                "relative_path": tool_input.tool_args["relative_path"],
            },
            llm_context=llm_context,
            summary=(
                "Read file: "
                f"{tool_input.tool_args['repository_id']}/"
                f"{tool_input.tool_args['relative_path']}"
            ),
        )


class GetRuntimeStatusTool(JarvisCapabilityTool):
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
        "read-only. Prefer wording such as 'The Windows Agent is currently "
        "reachable and reports status ok.' when the backend returns status "
        "ok."
    )
    parameters = vol.Schema({})

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on runtime health capability."""
        return await self._execute_capability(
            capability="system.health",
            parameters={},
            llm_context=llm_context,
            summary="Check Windows Agent reachability",
        )


class GetRuntimeInfoTool(JarvisCapabilityTool):
    """Tool for retrieving desktop runtime information."""

    name = "get_runtime_info"
    description = (
        "Use when the user asks for Windows Agent information, hostname, "
        "operating system, platform, architecture, or Python runtime "
        "information. This is read-only."
    )
    parameters = vol.Schema({})

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on runtime information capability."""
        return await self._execute_capability(
            capability="system.info",
            parameters={},
            llm_context=llm_context,
            summary="Get Windows Agent runtime information",
        )


class GetRuntimeCapabilitiesTool(JarvisCapabilityTool):
    """Tool for listing desktop runtime capabilities."""

    name = "get_runtime_capabilities"
    description = (
        "Use when the user asks what the Windows Agent can do, which "
        "capabilities the Windows Agent exposes, or which Windows Agent "
        "functions are available. This returns the Agent's implemented "
        "capability inventory for discovery only; it does not mean every "
        "listed capability is directly callable through Companion tools. "
        "This is read-only."
    )
    parameters = vol.Schema({})

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on runtime capabilities capability."""
        return await self._execute_capability(
            capability="system.capabilities",
            parameters={},
            llm_context=llm_context,
            summary="Get Windows Agent capability inventory",
        )


class GetSystemMetricsTool(JarvisCapabilityTool):
    """Tool for retrieving a live desktop runtime metrics snapshot."""

    name = "get_system_metrics"
    description = (
        "Use for current Windows PC metrics such as CPU usage, CPU "
        "temperature, GPU usage, GPU temperature, RAM usage, drive usage, "
        "free disk space, uptime, network totals, or overall current PC "
        "status. This retrieves one live system-measurements snapshot through "
        "Project-JARVIS. Answer only with metrics relevant to the user's "
        "question; do not dump the full raw result unless explicitly asked. "
        "Nullable or missing metric values mean unavailable, not zero. Do "
        "not use for project documentation, historical trends, Home "
        "Assistant entity values, process lists, services, files, Git, or "
        "long-term stability claims. This is read-only."
    )
    parameters = vol.Schema({})

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on runtime metrics capability."""
        return await self._execute_capability(
            capability="system.metrics",
            parameters={},
            llm_context=llm_context,
            summary="Get Windows PC system metrics",
        )


APPROVED_APPLICATION_IDS = frozenset(
    {"chrome", "discord", "notepad", "obsidian", "steam", "visual_studio"}
)
APPLICATION_SUMMARIES = {
    "chrome": "Open Google Chrome",
    "discord": "Open Discord",
    "notepad": "Open Notepad",
    "obsidian": "Open Obsidian",
    "steam": "Open Steam",
    "visual_studio": "Open Visual Studio",
}


def _approved_application_id(value: object) -> str:
    if value not in APPROVED_APPLICATION_IDS:
        raise ValueError("application_id is not approved for launch")

    return str(value)


class LaunchApplicationTool(JarvisCapabilityTool):
    """Tool for launching one approved registered Windows application."""

    name = "launch_application"
    description = (
        "Use when the user explicitly asks to open, start, or launch Visual "
        "Studio, including 'Oeffne Visual Studio', 'Starte Visual Studio', "
        "'Launch Visual Studio', or 'Mach Visual Studio auf', and when the "
        "user asks to open Notepad, den Editor, Chrome, Discord, Steam, or "
        "Obsidian. Supported application_id values are visual_studio, "
        "notepad, chrome, discord, steam, and obsidian. Do not use this for ambiguous "
        "'VS' requests because that may mean Visual Studio Code; ask for "
        "clarification. Do not claim Visual Studio Code support. This tool "
        "accepts no paths, arguments, working directories, environment "
        "variables, discovery settings, or local overrides."
    )
    parameters = vol.Schema(
        {
            vol.Required("application_id"): vol.All(str, _approved_application_id),
        }
    )

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on application.launch capability."""
        application_id = tool_input.tool_args["application_id"]
        return await self._execute_capability(
            capability="application.launch",
            parameters={
                "application_id": application_id,
            },
            llm_context=llm_context,
            summary=APPLICATION_SUMMARIES[str(application_id)],
        )


APPROVED_DEVICE_POWER_IDS = frozenset({"gaming_pc"})
APPROVED_DEVICE_POWER_ACTIONS = frozenset({"wake"})
DEVICE_POWER_SUMMARIES = {
    ("gaming_pc", "wake"): "Wake Gaming-PC",
}


def _approved_device_power_id(value: object) -> str:
    if value not in APPROVED_DEVICE_POWER_IDS:
        raise ValueError("device_id is not approved for power control")

    return str(value)


def _approved_device_power_action(value: object) -> str:
    if value not in APPROVED_DEVICE_POWER_ACTIONS:
        raise ValueError("action is not approved for device power control")

    return str(value)


class ControlDevicePowerTool(JarvisCapabilityTool):
    """Tool for one approved registered device power action."""

    name = "control_device_power"
    description = (
        "Use when the user explicitly asks to wake, start, turn on, "
        "einschalten, starten, wecken, or mach an the registered Gaming-PC "
        "or main PC. Supported device_id is gaming_pc. Supported action is "
        "wake. This forwards to Project-JARVIS device.power and does not "
        "call Home Assistant directly. It accepts no MAC address, IP address, "
        "broadcast address, port, entity, script, domain, service, or raw "
        "payload. Success means the Wake-on-LAN request was sent, not that "
        "the PC booted or is ready."
    )
    parameters = vol.Schema(
        {
            vol.Required("device_id"): vol.All(str, _approved_device_power_id),
            vol.Required("action"): vol.All(str, _approved_device_power_action),
        }
    )

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the JARVIS Add-on device.power capability."""
        device_id = str(tool_input.tool_args["device_id"])
        action = str(tool_input.tool_args["action"])

        return await self._execute_capability(
            capability="device.power",
            parameters={
                "device_id": device_id,
                "action": action,
            },
            llm_context=llm_context,
            summary=DEVICE_POWER_SUMMARIES[(device_id, action)],
        )


class GetActivationStatusTool(llm.Tool):
    """Tool for checking one stored provider activation."""

    name = "get_activation_status"
    description = (
        "Use for natural follow-up questions about pending JARVIS activation "
        "work, such as whether the PC is ready, whether everything finished, "
        "whether the user can continue, or how far the request is. "
        "activation_id is optional; omit it when the active activation can be "
        "resolved from the current conversation. Set include_all when the user "
        "asks whether everything is finished."
    )
    parameters = vol.Schema(
        {
            vol.Optional("activation_id"): vol.All(str, vol.Length(min=1)),
            vol.Optional("summary_hint"): vol.All(str, vol.Length(min=1)),
            vol.Optional("include_all"): bool,
        }
    )

    def __init__(self, activation_workflow: ActivationWorkflow) -> None:
        self._activation_workflow = activation_workflow

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        return await self._activation_workflow.get_follow_up_status(
            activation_id=tool_input.tool_args.get("activation_id"),
            conversation_context_id=_conversation_context_id(llm_context),
            summary_hint=tool_input.tool_args.get("summary_hint"),
            include_all=bool(tool_input.tool_args.get("include_all", False)),
        )


class ConfirmActivationTool(llm.Tool):
    """Tool for confirming one pending provider activation."""

    name = "confirm_activation"
    description = (
        "Use only after the user explicitly agrees to wake the PC for a "
        "pending activation. activation_id is optional when the current "
        "conversation has exactly one pending confirmation."
    )
    parameters = vol.Schema(
        {
            vol.Optional("activation_id"): vol.All(str, vol.Length(min=1)),
            vol.Optional("summary_hint"): vol.All(str, vol.Length(min=1)),
        }
    )

    def __init__(self, activation_workflow: ActivationWorkflow) -> None:
        self._activation_workflow = activation_workflow

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        return await self._activation_workflow.confirm_follow_up(
            activation_id=tool_input.tool_args.get("activation_id"),
            conversation_context_id=_conversation_context_id(llm_context),
            summary_hint=tool_input.tool_args.get("summary_hint"),
        )


class RetryActivationTool(llm.Tool):
    """Tool for accepting one retry-waiting provider activation."""

    name = "retry_activation"
    description = (
        "Use only after the user explicitly agrees to retry a specific "
        "activation that is waiting for retry confirmation. activation_id is "
        "optional when the current conversation has exactly one retry-waiting "
        "activation."
    )
    parameters = vol.Schema(
        {
            vol.Optional("activation_id"): vol.All(str, vol.Length(min=1)),
            vol.Optional("summary_hint"): vol.All(str, vol.Length(min=1)),
        }
    )

    def __init__(self, activation_workflow: ActivationWorkflow) -> None:
        self._activation_workflow = activation_workflow

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        return await self._activation_workflow.retry_follow_up(
            activation_id=tool_input.tool_args.get("activation_id"),
            conversation_context_id=_conversation_context_id(llm_context),
            summary_hint=tool_input.tool_args.get("summary_hint"),
        )


class CancelActivationTool(llm.Tool):
    """Tool for cancelling one provider activation."""

    name = "cancel_activation"
    description = (
        "Use when the user says no, cancel, never mind, or stop for a "
        "pending or retry-waiting activation. activation_id is optional when "
        "the current conversation has exactly one active activation."
    )
    parameters = vol.Schema(
        {
            vol.Optional("activation_id"): vol.All(str, vol.Length(min=1)),
            vol.Optional("summary_hint"): vol.All(str, vol.Length(min=1)),
        }
    )

    def __init__(self, activation_workflow: ActivationWorkflow) -> None:
        self._activation_workflow = activation_workflow

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        return await self._activation_workflow.cancel_follow_up(
            activation_id=tool_input.tool_args.get("activation_id"),
            conversation_context_id=_conversation_context_id(llm_context),
            summary_hint=tool_input.tool_args.get("summary_hint"),
        )


def _conversation_context_id(llm_context: llm.LLMContext) -> str | None:
    """Best-effort extraction of a Home Assistant conversation context id."""
    for attribute in ("context_id", "conversation_id", "id"):
        value = getattr(llm_context, attribute, None)

        if isinstance(value, str) and value:
            return value

    context = getattr(llm_context, "context", None)
    value = getattr(context, "id", None)

    if isinstance(value, str) and value:
        return value

    return None


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
