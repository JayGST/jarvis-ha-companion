"""Tests for the Home Assistant LLM API boundary."""

from __future__ import annotations

import inspect

import pytest

from homeassistant.helpers import llm

from custom_components.jarvis_ha_companion.llm import (
    CAPABILITY_GUIDANCE,
    COMPANION_TOOL_INSTRUCTIONS,
    FALLBACK_IDENTITY_PROMPT,
    FindDecisionTool,
    GetIdeasTool,
    GetRoadmapItemsTool,
    GetRuntimeCapabilitiesTool,
    GetRuntimeInfoTool,
    GetRuntimeStatusTool,
    GetSystemMetricsTool,
    InspectProjectModuleTool,
    JarvisLLMAPI,
    ListRepositoryDirectoryTool,
    ListCapabilitiesTool,
    ListExtensionsTool,
    ReadRepositoryFileTool,
    RepositoryFileExistsTool,
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

    assert source.count("execute_capability(") == 4
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

    assert source.count("execute_capability(") == 3
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
