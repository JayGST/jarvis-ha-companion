"""Tests for the Home Assistant LLM API boundary."""

from __future__ import annotations

import inspect

import pytest

from homeassistant.helpers import llm

from custom_components.jarvis_ha_companion.llm import (
    CAPABILITY_GUIDANCE,
    CancelActivationTool,
    COMPANION_TOOL_INSTRUCTIONS,
    FALLBACK_IDENTITY_PROMPT,
    ConfirmActivationTool,
    ControlDevicePowerTool,
    FindDecisionTool,
    GetActivationStatusTool,
    GetIdeasTool,
    GetRoadmapItemsTool,
    GetRuntimeCapabilitiesTool,
    GetRuntimeInfoTool,
    GetRuntimeStatusTool,
    GetSystemMetricsTool,
    InspectProjectModuleTool,
    JarvisLLMAPI,
    LaunchApplicationTool,
    ListRepositoryDirectoryTool,
    ListCapabilitiesTool,
    ListExtensionsTool,
    ReadRepositoryFileTool,
    RepositoryFileExistsTool,
    RetryActivationTool,
    SearchProjectTool,
    build_api_prompt,
)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def execute_capability(
        self,
        *,
        capability: str,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        self.calls.append((capability, parameters))
        return {"result": {"capability": capability, "parameters": parameters}}


class FakeActivationWorkflow:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def observe_capability_response(
        self,
        response: dict[str, object],
        *,
        conversation_context_id: str | None,
        capability_name: str,
        user_facing_summary: str,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "response": response,
                "conversation_context_id": conversation_context_id,
                "capability_name": capability_name,
                "user_facing_summary": user_facing_summary,
            }
        )
        return response


def test_build_api_prompt_includes_runtime_identity_in_order() -> None:
    """The prompt starts with runtime identity, then Companion instructions."""
    prompt = build_api_prompt("Canonical runtime identity.")

    assert prompt.startswith("Canonical runtime identity.\n\n")
    assert prompt.index("Canonical runtime identity.") < prompt.index(
        COMPANION_TOOL_INSTRUCTIONS
    )
    assert prompt.index(COMPANION_TOOL_INSTRUCTIONS) < prompt.index(
        CAPABILITY_GUIDANCE
    )


def test_build_api_prompt_removes_static_duplicate_identity() -> None:
    """The Companion no longer owns the old personality summary."""
    prompt = build_api_prompt("Canonical runtime identity.")

    assert "Canonical runtime identity." in prompt
    assert "calm, precise, reliable personal assistant" not in prompt
    assert "composed and subtly dry communication style" not in prompt
    assert "Answer as JARVIS, not as a generic Home Assistant assistant" not in prompt


def test_build_api_prompt_uses_neutral_fallback() -> None:
    """Fallback avoids restoring duplicate identity text."""
    prompt = build_api_prompt(None)

    assert prompt.startswith(FALLBACK_IDENTITY_PROMPT)
    assert "calm, precise, reliable personal assistant" not in prompt
    assert "composed and subtly dry communication style" not in prompt


@pytest.mark.asyncio
async def test_llm_api_uses_cached_prompt_for_instances() -> None:
    """API instances reuse the prompt passed at API construction time."""
    client = FakeClient()
    api = JarvisLLMAPI(object(), client, "Canonical runtime identity.")

    first = await api.async_get_api_instance(llm.LLMContext())
    second = await api.async_get_api_instance(llm.LLMContext())

    assert first.api_prompt == second.api_prompt
    assert first.api_prompt.startswith("Canonical runtime identity.")
    assert client.calls == []


@pytest.mark.asyncio
async def test_registered_llm_tools_forward_to_existing_capabilities() -> None:
    """Existing LLM tools still forward directly to the Add-on client."""
    client = FakeClient()
    expected_tool_names = {
        "inspect_project_module",
        "list_capabilities",
        "list_extensions",
        "get_ideas",
        "get_roadmap_items",
        "find_decision",
        "search_project",
        "repository_file_exists",
        "list_repository_directory",
        "read_repository_file",
        "get_runtime_status",
        "get_runtime_info",
        "get_runtime_capabilities",
        "get_system_metrics",
        "launch_application",
        "control_device_power",
        "get_activation_status",
        "confirm_activation",
        "retry_activation",
        "cancel_activation",
    }
    api = JarvisLLMAPI(object(), client, "Canonical runtime identity.")
    instance = await api.async_get_api_instance(llm.LLMContext())

    assert {tool.name for tool in instance.tools} == expected_tool_names

    inspect_result = await InspectProjectModuleTool(client).async_call(
        object(),
        llm.ToolInput({"module_name": "Windows Agent"}),
        llm.LLMContext(),
    )
    capabilities_result = await ListCapabilitiesTool(client).async_call(
        object(),
        llm.ToolInput({}),
        llm.LLMContext(),
    )
    extensions_result = await ListExtensionsTool(client).async_call(
        object(),
        llm.ToolInput({}),
        llm.LLMContext(),
    )
    ideas_result = await GetIdeasTool(client).async_call(
        object(),
        llm.ToolInput({}),
        llm.LLMContext(),
    )
    roadmap_result = await GetRoadmapItemsTool(client).async_call(
        object(),
        llm.ToolInput({}),
        llm.LLMContext(),
    )
    decision_result = await FindDecisionTool(client).async_call(
        object(),
        llm.ToolInput({}),
        llm.LLMContext(),
    )
    search_result = await SearchProjectTool(client).async_call(
        object(),
        llm.ToolInput({"query": "identity decisions"}),
        llm.LLMContext(),
    )
    exists_result = await RepositoryFileExistsTool(client).async_call(
        object(),
        llm.ToolInput(
            {
                "repository_id": "companion",
                "relative_path": "README.md",
            }
        ),
        llm.LLMContext(),
    )
    directory_result = await ListRepositoryDirectoryTool(client).async_call(
        object(),
        llm.ToolInput(
            {
                "repository_id": "companion",
                "relative_path": "docs",
            }
        ),
        llm.LLMContext(),
    )
    read_result = await ReadRepositoryFileTool(client).async_call(
        object(),
        llm.ToolInput(
            {
                "repository_id": "companion",
                "relative_path": "README.md",
            }
        ),
        llm.LLMContext(),
    )
    runtime_result = await GetRuntimeStatusTool(client).async_call(
        object(),
        llm.ToolInput({}),
        llm.LLMContext(),
    )
    runtime_info_result = await GetRuntimeInfoTool(client).async_call(
        object(),
        llm.ToolInput({}),
        llm.LLMContext(),
    )
    runtime_capabilities_result = await GetRuntimeCapabilitiesTool(client).async_call(
        object(),
        llm.ToolInput({}),
        llm.LLMContext(),
    )
    system_metrics_result = await GetSystemMetricsTool(client).async_call(
        object(),
        llm.ToolInput({}),
        llm.LLMContext(),
    )
    launch_result = await LaunchApplicationTool(client).async_call(
        object(),
        llm.ToolInput({"application_id": "visual_studio"}),
        llm.LLMContext(),
    )
    notepad_result = await LaunchApplicationTool(client).async_call(
        object(),
        llm.ToolInput({"application_id": "notepad"}),
        llm.LLMContext(),
    )
    chrome_result = await LaunchApplicationTool(client).async_call(
        object(),
        llm.ToolInput({"application_id": "chrome"}),
        llm.LLMContext(),
    )
    device_power_result = await ControlDevicePowerTool(client).async_call(
        object(),
        llm.ToolInput({"device_id": "gaming_pc", "action": "wake"}),
        llm.LLMContext(),
    )

    assert inspect_result["result"]["capability"] == "inspect_project_module"
    assert capabilities_result["result"]["capability"] == "list_capabilities"
    assert extensions_result["result"]["capability"] == "list_extensions"
    assert ideas_result["result"]["capability"] == "get_ideas"
    assert roadmap_result["result"]["capability"] == "get_roadmap_items"
    assert decision_result["result"]["capability"] == "find_decision"
    assert search_result["result"]["capability"] == "search_project"
    assert exists_result["result"]["capability"] == "filesystem.file_exists"
    assert directory_result["result"]["capability"] == "filesystem.list_directory"
    assert read_result["result"]["capability"] == "filesystem.read_file"
    assert runtime_result["result"]["capability"] == "system.health"
    assert runtime_info_result["result"]["capability"] == "system.info"
    assert (
        runtime_capabilities_result["result"]["capability"]
        == "system.capabilities"
    )
    assert system_metrics_result["result"]["capability"] == "system.metrics"
    assert launch_result["result"]["capability"] == "application.launch"
    assert notepad_result["result"]["capability"] == "application.launch"
    assert chrome_result["result"]["capability"] == "application.launch"
    assert device_power_result["result"]["capability"] == "device.power"
    assert client.calls == [
        ("inspect_project_module", {"module_name": "Windows Agent"}),
        ("list_capabilities", {}),
        ("list_extensions", {}),
        ("get_ideas", {}),
        ("get_roadmap_items", {}),
        ("find_decision", {}),
        ("search_project", {"query": "identity decisions"}),
        (
            "filesystem.file_exists",
            {"repository_id": "companion", "relative_path": "README.md"},
        ),
        (
            "filesystem.list_directory",
            {"repository_id": "companion", "relative_path": "docs"},
        ),
        (
            "filesystem.read_file",
            {"repository_id": "companion", "relative_path": "README.md"},
        ),
        ("system.health", {}),
        ("system.info", {}),
        ("system.capabilities", {}),
        ("system.metrics", {}),
        ("application.launch", {"application_id": "visual_studio"}),
        ("application.launch", {"application_id": "notepad"}),
        ("application.launch", {"application_id": "chrome"}),
        ("device.power", {"device_id": "gaming_pc", "action": "wake"}),
    ]


@pytest.mark.asyncio
async def test_runtime_status_tool_has_no_parameters_and_fixed_mapping() -> None:
    """Runtime status cannot accept user-controlled capabilities or parameters."""
    client = FakeClient()
    tool = GetRuntimeStatusTool(client)

    result = await tool.async_call(
        object(),
        llm.ToolInput(
            {
                "capability": "arbitrary.capability",
                "parameters": {"write": True},
                "provider": "windows-agent",
            }
        ),
        llm.LLMContext(),
    )

    assert tool.parameters.schema == {}
    assert client.calls == [("system.health", {})]
    assert result == {
        "result": {
            "capability": "system.health",
            "parameters": {},
        }
    }


@pytest.mark.asyncio
async def test_runtime_info_tool_has_no_parameters_and_fixed_mapping() -> None:
    """Runtime info cannot accept user-controlled capabilities or parameters."""
    client = FakeClient()
    tool = GetRuntimeInfoTool(client)

    result = await tool.async_call(
        object(),
        llm.ToolInput(
            {
                "capability": "arbitrary.capability",
                "parameters": {"path": "C:/"},
                "provider": "windows-agent",
            }
        ),
        llm.LLMContext(),
    )

    assert tool.parameters.schema == {}
    assert client.calls == [("system.info", {})]
    assert result == {
        "result": {
            "capability": "system.info",
            "parameters": {},
        }
    }


@pytest.mark.asyncio
async def test_runtime_capabilities_tool_has_no_parameters_and_fixed_mapping() -> None:
    """Runtime capabilities cannot accept user-controlled capabilities."""
    client = FakeClient()
    tool = GetRuntimeCapabilitiesTool(client)

    result = await tool.async_call(
        object(),
        llm.ToolInput(
            {
                "capability": "arbitrary.capability",
                "parameters": {"write": True},
                "provider": "windows-agent",
            }
        ),
        llm.LLMContext(),
    )

    assert tool.parameters.schema == {}
    assert client.calls == [("system.capabilities", {})]
    assert result == {
        "result": {
            "capability": "system.capabilities",
            "parameters": {},
        }
    }


@pytest.mark.asyncio
async def test_system_metrics_tool_has_no_parameters_and_fixed_mapping() -> None:
    """System metrics cannot accept user-controlled capabilities or parameters."""
    client = FakeClient()
    tool = GetSystemMetricsTool(client)

    result = await tool.async_call(
        object(),
        llm.ToolInput(
            {
                "capability": "filesystem.write_file",
                "parameters": {"path": "C:/"},
                "provider": "windows-agent",
                "owner": "companion",
                "routing": "direct",
                "endpoint": "http://127.0.0.1",
            }
        ),
        llm.LLMContext(),
    )

    assert tool.parameters.schema == {}
    assert client.calls == [("system.metrics", {})]
    assert result == {
        "result": {
            "capability": "system.metrics",
            "parameters": {},
        }
    }


@pytest.mark.asyncio
async def test_launch_application_tool_uses_application_enum_and_fixed_mapping() -> None:
    """Application launch exposes only the approved application identifier."""
    client = FakeClient()
    tool = LaunchApplicationTool(client)
    schema_keys = {key.key for key in tool.parameters.schema}

    result = await tool.async_call(
        object(),
        llm.ToolInput(
            {
                "application_id": "visual_studio",
                "path": "C:/Program Files/App/app.exe",
                "arguments": ["--unsafe"],
                "working_directory": "C:/",
                "environment": {"SECRET": "value"},
                "capability": "filesystem.write_text_file",
                "provider": "windows-agent",
            }
        ),
        llm.LLMContext(),
    )

    assert schema_keys == {"application_id"}
    assert tool.parameters({"application_id": "visual_studio"}) == {
        "application_id": "visual_studio"
    }
    assert tool.parameters({"application_id": "notepad"}) == {
        "application_id": "notepad"
    }
    for application_id in ("chrome", "discord", "steam", "obsidian"):
        assert tool.parameters({"application_id": application_id}) == {
            "application_id": application_id
        }
    with pytest.raises(Exception):
        tool.parameters({"application_id": "visual_studio_code"})
    assert client.calls == [("application.launch", {"application_id": "visual_studio"})]
    assert result == {
        "result": {
            "capability": "application.launch",
            "parameters": {"application_id": "visual_studio"},
        }
    }


@pytest.mark.asyncio
async def test_launch_application_tool_passes_application_activation_summary() -> None:
    """The same launch adapter supplies resource-specific activation summaries."""
    client = FakeClient()
    workflow = FakeActivationWorkflow()
    tool = LaunchApplicationTool(client, workflow)

    await tool.async_call(
        object(),
        llm.ToolInput({"application_id": "notepad"}),
        llm.LLMContext(),
    )

    assert client.calls == [("application.launch", {"application_id": "notepad"})]
    assert workflow.calls[0]["capability_name"] == "application.launch"
    assert workflow.calls[0]["user_facing_summary"] == "Open Notepad"


def test_launch_application_guidance_supports_notepad_and_rejects_vscode_claims() -> None:
    """Prompt guidance narrows launch phrasing and avoids VS Code support."""
    prompt = build_api_prompt("Canonical runtime identity.")
    description = LaunchApplicationTool(FakeClient()).description

    assert "Use launch_application" in prompt
    assert "visual_studio" in prompt
    assert "notepad" in prompt
    assert "chrome" in prompt
    assert "discord" in prompt
    assert "steam" in prompt
    assert "obsidian" in prompt
    assert "Windows Editor" in prompt
    assert "Do not treat 'VS' as sufficient" in prompt
    assert "Visual Studio Code" in prompt
    assert "Do not claim support for Visual Studio Code" in prompt
    assert "paths, arguments, working directories" in prompt
    assert "discovery settings, or local overrides" in prompt
    assert "Mach Visual Studio auf" in description
    assert "den Editor" in description
    assert "Chrome" in description
    assert "Discord" in description
    assert "Steam" in description
    assert "Obsidian" in description
    assert "Visual Studio Code" in description


def test_runtime_guidance_requires_fresh_status_checks_without_stability_claims() -> None:
    """Prompt guidance keeps runtime status claims narrow."""
    prompt = build_api_prompt("Canonical runtime identity.")
    description = GetRuntimeStatusTool(FakeClient()).description

    assert "Status questions require a fresh tool call" in prompt
    assert "reachable Windows Agent means the Windows PC is currently running" in prompt
    assert "does not prove long-term stability" in prompt
    assert "screen state, user presence, lock state, workload, or standby details" in prompt
    assert "Do not claim the agent is stable" in prompt
    assert "currently reachable and reports status ok" in prompt
    assert "currently reachable and reports status ok" in description
    assert "runs stably" not in prompt
    assert "is permanently stable" not in prompt
    assert "has no problems" not in prompt
    assert "direct Windows Agent" not in prompt


def test_capability_guidance_distinguishes_agent_inventory_from_companion_tools() -> None:
    """Capability questions separate implementation inventory from tool access."""
    prompt = build_api_prompt("Canonical runtime identity.")
    description = GetRuntimeCapabilitiesTool(FakeClient()).description

    assert "distinguish three layers clearly" in prompt
    assert "Windows Agent capabilities are operations implemented and advertised" in prompt
    assert "discovering them does not grant permission" in prompt
    assert "does not mean Claude can call them" in prompt
    assert "Project-JARVIS routed capabilities" in prompt
    assert "subject to authorization and policy" in prompt
    assert "Companion tools are the only operations Claude can directly invoke" in prompt
    assert "fixed allowlisted mappings only" in prompt
    assert "The Windows Agent implements these capabilities" in prompt
    assert "I can directly use only the explicitly exposed tools" in prompt
    assert "Agent's implemented capability inventory" in prompt
    assert "does not mean every listed capability is directly callable" in description


def test_capability_guidance_does_not_expose_write_git_task_scope_or_audit() -> None:
    """Discovery guidance prevents unsupported capabilities from sounding callable."""
    prompt = build_api_prompt("Canonical runtime identity.")

    assert "runtime status" in prompt
    assert "runtime information" in prompt
    assert "runtime capability discovery" in prompt
    assert "live system metrics" in prompt
    assert "deterministic Project Search" in prompt
    assert "approved repository file existence checks" in prompt
    assert "approved repository directory listing" in prompt
    assert "approved small UTF-8 repository file reads" in prompt
    assert "Do not describe write, Git, Task Scope, audit" in prompt
    assert "directly callable unless a dedicated Companion tool exists" in prompt
    assert "write, Git, Task Scope, audit" in prompt


def test_system_metrics_guidance_selects_live_metrics_questions() -> None:
    """Prompt guidance routes current PC metric questions to metrics."""
    prompt = build_api_prompt("Canonical runtime identity.")
    description = GetSystemMetricsTool(FakeClient()).description

    assert "Use get_system_metrics for questions about current Windows PC metrics" in prompt
    assert "CPU usage" in prompt
    assert "CPU temperature" in prompt
    assert "GPU usage" in prompt
    assert "GPU temperature" in prompt
    assert "RAM usage" in prompt
    assert "drive usage" in prompt
    assert "free disk space" in prompt
    assert "uptime" in prompt
    assert "network totals" in prompt
    assert "overall current PC status" in prompt
    assert "current Windows PC metrics" in description


def test_system_metrics_guidance_answers_selectively_and_handles_nulls() -> None:
    """Metric responses stay focused and treat nullable values as unavailable."""
    prompt = build_api_prompt("Canonical runtime identity.")
    description = GetSystemMetricsTool(FakeClient()).description

    assert "answer only with metrics relevant to the user's question" in prompt
    assert "Do not dump the raw complete result" in prompt
    assert "unless the user explicitly asks for all raw metrics" in prompt
    assert "Nullable or missing metric values mean unavailable, not zero" in prompt
    assert "do not infer values" in prompt
    assert "do not describe unavailable sensors as errors" in prompt
    assert "Answer only with metrics relevant" in description
    assert "unavailable, not zero" in description


def test_system_metrics_guidance_keeps_health_and_metrics_distinct() -> None:
    """Runtime health checks and system measurements remain separate tools."""
    prompt = build_api_prompt("Canonical runtime identity.")
    description = GetSystemMetricsTool(FakeClient()).description

    assert "get_runtime_status checks current reachability and reported health" in prompt
    assert "get_system_metrics retrieves current system measurements" in prompt
    assert "Do not use get_system_metrics for project documentation" in prompt
    assert "historical trends, Home Assistant entity values, process lists" in prompt
    assert "services, files, Git, or long-term stability claims" in prompt
    assert "Metrics alone do not prove long-term stability" in prompt
    assert "absence of problems, screen state, user presence, standby state" in prompt
    assert "future performance" in prompt
    assert "process lists, services, files, Git" in description


def test_runtime_tools_do_not_route_or_contact_windows_agent_directly() -> None:
    """Runtime tools stay behind JarvisAddonClient instead of direct transports."""
    source = "\n".join(
        inspect.getsource(tool)
        for tool in (
            GetRuntimeStatusTool,
            GetRuntimeInfoTool,
            GetRuntimeCapabilitiesTool,
            GetSystemMetricsTool,
        )
    )

    assert source.count("_execute_capability(") == 4
    assert "system.health" in source
    assert "system.info" in source
    assert "system.capabilities" in source
    assert "system.metrics" in source
    assert "async_get_clientsession" not in source
    assert "requests" not in source
    assert "httpx" not in source
    assert "subprocess" not in source
    assert "psutil" not in source
    assert "win32" not in source
    assert "provider" not in source
    assert "route" not in source.lower()
    assert "filesystem.write" not in source


def test_launch_application_tool_has_no_direct_windows_or_process_access() -> None:
    """Launch requests stay behind Project-JARVIS fixed capability execution."""
    source = inspect.getsource(LaunchApplicationTool)

    assert source.count("_execute_capability(") == 1
    assert "application.launch" in source
    assert "visual_studio" in source
    assert "notepad" in source
    assert "chrome" in source
    assert "discord" in source
    assert "steam" in source
    assert "obsidian" in source
    assert "launch_notepad" not in source
    assert "launch_chrome" not in source
    assert "subprocess" not in source
    assert "Popen" not in source
    assert "async_get_clientsession" not in source
    assert "requests." not in source
    assert "httpx" not in source
    assert "provider" not in source
    assert "route" not in source.lower()
    assert "working_directory" not in source


@pytest.mark.asyncio
async def test_control_device_power_tool_schema_and_fixed_mapping() -> None:
    """Device power exposes only approved device/action enums."""
    client = FakeClient()
    tool = ControlDevicePowerTool(client)
    schema_keys = {key.key for key in tool.parameters.schema}

    result = await tool.async_call(
        object(),
        llm.ToolInput(
            {
                "device_id": "gaming_pc",
                "action": "wake",
                "domain": "wake_on_lan",
                "service": "send_magic_packet",
                "mac_address": "00:00:00:00:00:00",
                "broadcast_address": "127.0.0.1",
                "port": 1,
                "entity_id": "switch.gaming_pc",
                "script": "script.wake_pc",
            }
        ),
        llm.LLMContext(),
    )

    assert schema_keys == {"device_id", "action"}
    assert tool.parameters({"device_id": "gaming_pc", "action": "wake"}) == {
        "device_id": "gaming_pc",
        "action": "wake",
    }
    with pytest.raises(Exception):
        tool.parameters({"device_id": "desktop", "action": "wake"})
    with pytest.raises(Exception):
        tool.parameters({"device_id": "gaming_pc", "action": "shutdown"})
    assert client.calls == [("device.power", {"device_id": "gaming_pc", "action": "wake"})]
    assert result == {
        "result": {
            "capability": "device.power",
            "parameters": {"device_id": "gaming_pc", "action": "wake"},
        }
    }


@pytest.mark.asyncio
async def test_control_device_power_tool_passes_activation_summary() -> None:
    """The device power adapter supplies a request-specific summary."""
    client = FakeClient()
    workflow = FakeActivationWorkflow()
    tool = ControlDevicePowerTool(client, workflow)

    await tool.async_call(
        object(),
        llm.ToolInput({"device_id": "gaming_pc", "action": "wake"}),
        llm.LLMContext(),
    )

    assert client.calls == [("device.power", {"device_id": "gaming_pc", "action": "wake"})]
    assert workflow.calls[0]["capability_name"] == "device.power"
    assert workflow.calls[0]["user_facing_summary"] == "Wake Gaming-PC"


def test_control_device_power_guidance_avoids_readiness_claims() -> None:
    """Prompt and tool text define wake semantics narrowly."""
    prompt = build_api_prompt("Canonical runtime identity.")
    description = ControlDevicePowerTool(FakeClient()).description

    assert "Use control_device_power" in prompt
    assert "device_id is gaming_pc" in prompt
    assert "only supported action is wake" in prompt
    assert "does not prove the PC booted" in prompt
    assert "Windows Agent is reachable" in prompt
    assert "arbitrary Home Assistant service calls" in prompt
    assert "does not call Home Assistant directly" in description
    assert "Success means the Wake-on-LAN request was sent" in description
    assert "not that the PC booted or is ready" in description


def test_control_device_power_tool_has_no_direct_home_assistant_access() -> None:
    """Device power stays behind Project-JARVIS fixed capability execution."""
    source = inspect.getsource(ControlDevicePowerTool)

    assert source.count("_execute_capability(") == 1
    assert "device.power" in source
    assert "gaming_pc" in source
    assert "wake" in source
    assert "async_get_clientsession" not in source
    assert "requests" not in source
    assert "httpx" not in source
    assert "wake_on_lan" not in source
    assert "call_service" not in source
    assert "send_magic_packet" not in source
    assert "entity_id" not in source
    assert "mac_address" not in source
    assert "broadcast_address" not in source


@pytest.mark.asyncio
async def test_search_project_tool_schema_and_fixed_mapping_with_query() -> None:
    """Search forwards only the required query to the fixed backend capability."""
    client = FakeClient()
    tool = SearchProjectTool(client)
    schema_keys = {key.key for key in tool.parameters.schema}

    result = await tool.async_call(
        object(),
        llm.ToolInput({"query": "runtime architecture"}),
        llm.LLMContext(),
    )

    assert schema_keys == {"query", "limit"}
    assert client.calls == [("search_project", {"query": "runtime architecture"})]
    assert result == {
        "result": {
            "capability": "search_project",
            "parameters": {"query": "runtime architecture"},
        }
    }


@pytest.mark.asyncio
async def test_search_project_tool_forwards_optional_limit() -> None:
    """Search forwards limit unchanged when the LLM supplies it."""
    client = FakeClient()

    await SearchProjectTool(client).async_call(
        object(),
        llm.ToolInput({"query": "roadmap open items", "limit": 3}),
        llm.LLMContext(),
    )

    assert client.calls == [
        ("search_project", {"query": "roadmap open items", "limit": 3})
    ]


@pytest.mark.asyncio
async def test_search_project_tool_ignores_unsupported_backend_inputs() -> None:
    """Search cannot be redirected with capability, provider, owner, or routing."""
    client = FakeClient()

    await SearchProjectTool(client).async_call(
        object(),
        llm.ToolInput(
            {
                "query": "architecture decisions",
                "limit": 5,
                "capability": "system.health",
                "provider": "windows-agent",
                "owner": "companion",
                "routing": "direct",
                "parameters": {"path": "C:/"},
            }
        ),
        llm.LLMContext(),
    )

    assert client.calls == [
        ("search_project", {"query": "architecture decisions", "limit": 5})
    ]


@pytest.mark.asyncio
async def test_search_project_tool_requires_query() -> None:
    """The tool implementation requires query before forwarding to the backend."""
    client = FakeClient()

    with pytest.raises(KeyError):
        await SearchProjectTool(client).async_call(
            object(),
            llm.ToolInput({"limit": 3}),
            llm.LLMContext(),
        )

    assert client.calls == []


def test_search_project_guidance_scope_and_summary_behavior() -> None:
    """Prompt guidance scopes project search to JARVIS project knowledge."""
    prompt = build_api_prompt("Canonical runtime identity.")

    assert "first consider search_project" in prompt
    assert "JARVIS architecture, roadmap, development, project decisions" in prompt
    assert "open items, engineering discussions" in prompt
    assert "implementation history, or project documentation" in prompt
    assert "Do not use search_project for general knowledge" in prompt
    assert "internet search, Windows filesystem search, or Home Assistant entity" in prompt
    assert "Summarize search results naturally" in prompt


def test_search_project_guidance_prefers_single_refinement_not_search_chains() -> None:
    """Prompt guidance avoids repeated speculative project searches."""
    prompt = build_api_prompt("Canonical runtime identity.")

    assert "Avoid repeated search_project calls" in prompt
    assert "perform at most one additional focused search" in prompt
    assert "Avoid chains of three or more speculative searches" in prompt


def test_search_project_guidance_preserves_specialized_tool_selection() -> None:
    """Prompt guidance keeps structured tools preferred for exact requests."""
    prompt = build_api_prompt("Canonical runtime identity.")
    description = SearchProjectTool(FakeClient()).description

    assert "Specialized tools such as find_decision" in prompt
    assert "inspect_project_module" in prompt
    assert "get_roadmap_items" in prompt
    assert "get_runtime_info" in prompt
    assert "remain better when the user clearly asks" in prompt
    assert "get_system_metrics" in prompt
    assert "Use specialized tools instead" in description
    assert "one specific ADR decision" in description
    assert "one specific implementation item" in description
    assert "Windows runtime status" in description


def test_search_project_guidance_uses_natural_source_language() -> None:
    """Prompt guidance hides internal filenames unless the user asks."""
    prompt = build_api_prompt("Canonical runtime identity.")

    assert "The project documentation describes" in prompt
    assert "The current roadmap plans" in prompt
    assert "The engineering notes indicate" in prompt
    assert "Do not say 'I searched ROADMAP.md'" in prompt
    assert "I searched OPEN_ITEMS.md" in prompt


def _filesystem_tool_expectations() -> tuple[tuple[object, str], ...]:
    client = FakeClient()
    return (
        (RepositoryFileExistsTool(client), "filesystem.file_exists"),
        (ListRepositoryDirectoryTool(client), "filesystem.list_directory"),
        (ReadRepositoryFileTool(client), "filesystem.read_file"),
    )


def test_repository_filesystem_tool_schemas_require_repository_and_path() -> None:
    """Filesystem tools require non-empty repository_id and relative_path."""
    for tool, _capability in _filesystem_tool_expectations():
        with pytest.raises(Exception):
            tool.parameters({})

        with pytest.raises(Exception):
            tool.parameters({"repository_id": "repo"})

        with pytest.raises(Exception):
            tool.parameters({"relative_path": "README.md"})

        with pytest.raises(Exception):
            tool.parameters({"repository_id": "", "relative_path": "README.md"})

        with pytest.raises(Exception):
            tool.parameters({"repository_id": "repo", "relative_path": ""})

        assert tool.parameters(
            {"repository_id": "repo", "relative_path": "README.md"}
        ) == {"repository_id": "repo", "relative_path": "README.md"}


def test_repository_filesystem_tool_schemas_do_not_expose_control_fields() -> None:
    """Filesystem tool schemas expose no backend control or absolute-path fields."""
    disallowed = {
        "capability",
        "provider",
        "owner",
        "routing",
        "endpoint",
        "windows_agent_url",
        "root",
        "absolute_path",
        "parameters",
    }

    for tool, _capability in _filesystem_tool_expectations():
        schema_keys = {key.key for key in tool.parameters.schema}

        assert schema_keys == {"repository_id", "relative_path"}
        assert schema_keys.isdisjoint(disallowed)


@pytest.mark.asyncio
async def test_repository_filesystem_tools_have_fixed_backend_mappings() -> None:
    """Filesystem tools call their fixed Project-JARVIS capabilities."""
    client = FakeClient()
    tool_expectations = (
        (RepositoryFileExistsTool(client), "filesystem.file_exists"),
        (ListRepositoryDirectoryTool(client), "filesystem.list_directory"),
        (ReadRepositoryFileTool(client), "filesystem.read_file"),
    )

    for tool, capability in tool_expectations:
        await tool.async_call(
            object(),
            llm.ToolInput(
                {
                    "repository_id": "companion",
                    "relative_path": "README.md",
                }
            ),
            llm.LLMContext(),
        )

        assert client.calls[-1] == (
            capability,
            {"repository_id": "companion", "relative_path": "README.md"},
        )


@pytest.mark.asyncio
async def test_repository_filesystem_tools_ignore_unsupported_control_inputs() -> None:
    """Filesystem tools cannot be redirected through unsupported inputs."""
    client = FakeClient()
    tool_expectations = (
        (RepositoryFileExistsTool(client), "filesystem.file_exists"),
        (ListRepositoryDirectoryTool(client), "filesystem.list_directory"),
        (ReadRepositoryFileTool(client), "filesystem.read_file"),
    )

    for tool, capability in tool_expectations:
        await tool.async_call(
            object(),
            llm.ToolInput(
                {
                    "repository_id": "companion",
                    "relative_path": "README.md",
                    "capability": "filesystem.write_file",
                    "provider": "windows-agent",
                    "owner": "companion",
                    "routing": "direct",
                    "endpoint": "http://127.0.0.1",
                    "windows_agent_url": "http://127.0.0.1",
                    "root": "C:/",
                    "absolute_path": "C:/Users/jonas/Desktop/secret.txt",
                    "parameters": {"operation": "write"},
                }
            ),
            llm.LLMContext(),
        )

        assert client.calls[-1] == (
            capability,
            {"repository_id": "companion", "relative_path": "README.md"},
        )


def test_repository_filesystem_guidance_sets_approved_repository_boundary() -> None:
    """Prompt guidance keeps filesystem access behind approved repositories."""
    prompt = build_api_prompt("Canonical runtime identity.")

    assert "Use repository_file_exists, list_repository_directory, and read_repository_file" in prompt
    assert "only for live files inside explicitly approved Windows Agent repositories" in prompt
    assert "Use search_project for synchronized Project Knowledge" in prompt
    assert "do not use repository filesystem tools for general project questions" in prompt
    assert "Do not claim access to arbitrary Desktop, Documents, drive, or system folder" in prompt
    assert "Do not invent repository IDs" in prompt
    assert "ask for the approved repository ID or relative path" in prompt
    assert "Absolute paths and parent-directory traversal are unavailable" in prompt
    assert "write, delete, move, and rename operations are unavailable" in prompt


def test_repository_filesystem_tools_do_not_route_or_contact_windows_agent_directly() -> None:
    """Filesystem tools stay behind JarvisAddonClient fixed mappings."""
    source = "\n".join(
        inspect.getsource(tool)
        for tool in (
            RepositoryFileExistsTool,
            ListRepositoryDirectoryTool,
            ReadRepositoryFileTool,
        )
    )

    assert source.count("_execute_capability(") == 3
    assert "filesystem.file_exists" in source
    assert "filesystem.list_directory" in source
    assert "filesystem.read_file" in source
    assert "async_get_clientsession" not in source
    assert "requests" not in source
    assert "httpx" not in source
    assert "subprocess" not in source
    assert "provider" not in source
    assert "route" not in source.lower()
    assert "filesystem.write" not in source
    assert "filesystem.delete" not in source
    assert "filesystem.rename" not in source
    assert "filesystem.move" not in source


@pytest.mark.asyncio
async def test_no_generic_filesystem_or_write_capable_tool_is_registered() -> None:
    """The Companion exposes only dedicated read-only filesystem tools."""
    client = FakeClient()
    api = JarvisLLMAPI(object(), client, "Canonical runtime identity.")
    instance = await api.async_get_api_instance(llm.LLMContext())
    tool_names = {tool.name for tool in instance.tools}

    filesystem_tool_names = {
        RepositoryFileExistsTool.name,
        ListRepositoryDirectoryTool.name,
        ReadRepositoryFileTool.name,
    }

    assert filesystem_tool_names == {
        "repository_file_exists",
        "list_repository_directory",
        "read_repository_file",
    }
    assert filesystem_tool_names.issubset(tool_names)
    assert "filesystem_execute" not in tool_names
    assert "write_repository_file" not in tool_names
    assert "delete_repository_file" not in tool_names
    assert "move_repository_file" not in tool_names
    assert "rename_repository_file" not in tool_names


def test_activation_tools_expose_only_activation_selection_fields() -> None:
    """Activation lifecycle tools expose no capability or provider controls."""
    status_schema_keys = {
        key.key for key in GetActivationStatusTool(object()).parameters.schema
    }
    action_tools = (
        ConfirmActivationTool(object()),
        RetryActivationTool(object()),
        CancelActivationTool(object()),
    )

    assert status_schema_keys == {"activation_id", "summary_hint", "include_all"}

    for tool in action_tools:
        schema_keys = {key.key for key in tool.parameters.schema}

        assert schema_keys == {"activation_id", "summary_hint"}


def test_activation_guidance_prevents_argument_resubmission_and_latest_guessing() -> None:
    """Prompt guidance keeps activation continuation server-owned."""
    prompt = build_api_prompt("Canonical runtime identity.")

    assert "activation_id as the handle for that exact request" in prompt
    assert "Never ask the user to repeat repository IDs" in prompt
    assert "Project-JARVIS stores the original request server-side" in prompt
    assert "confirm_activation" in prompt
    assert "retry_activation" in prompt
    assert "cancel_activation" in prompt
    assert "do not assume the latest" in prompt
    assert "Home Assistant conversations are request/response" in prompt
    assert "without another user message" in prompt
