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
    InspectProjectModuleTool,
    JarvisLLMAPI,
    ListCapabilitiesTool,
    ListExtensionsTool,
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
        "get_runtime_status",
        "get_runtime_info",
        "get_runtime_capabilities",
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

    assert inspect_result["result"]["capability"] == "inspect_project_module"
    assert capabilities_result["result"]["capability"] == "list_capabilities"
    assert extensions_result["result"]["capability"] == "list_extensions"
    assert ideas_result["result"]["capability"] == "get_ideas"
    assert roadmap_result["result"]["capability"] == "get_roadmap_items"
    assert decision_result["result"]["capability"] == "find_decision"
    assert runtime_result["result"]["capability"] == "system.health"
    assert runtime_info_result["result"]["capability"] == "system.info"
    assert (
        runtime_capabilities_result["result"]["capability"]
        == "system.capabilities"
    )
    assert client.calls == [
        ("inspect_project_module", {"module_name": "Windows Agent"}),
        ("list_capabilities", {}),
        ("list_extensions", {}),
        ("get_ideas", {}),
        ("get_roadmap_items", {}),
        ("find_decision", {}),
        ("system.health", {}),
        ("system.info", {}),
        ("system.capabilities", {}),
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


def test_runtime_guidance_requires_fresh_status_checks_without_stability_claims() -> None:
    """Prompt guidance keeps runtime status claims narrow."""
    prompt = build_api_prompt("Canonical runtime identity.")

    assert "Status questions require a fresh tool call" in prompt
    assert "reachable Windows Agent means the Windows PC is currently running" in prompt
    assert "does not prove long-term stability" in prompt
    assert "screen state, user presence, lock state, workload, or standby details" in prompt
    assert "Do not claim the agent is stable" in prompt
    assert "direct Windows Agent" not in prompt


def test_runtime_tools_do_not_route_or_contact_windows_agent_directly() -> None:
    """Runtime tools stay behind JarvisAddonClient instead of direct transports."""
    source = "\n".join(
        inspect.getsource(tool)
        for tool in (
            GetRuntimeStatusTool,
            GetRuntimeInfoTool,
            GetRuntimeCapabilitiesTool,
        )
    )

    assert source.count("execute_capability(") == 3
    assert "system.health" in source
    assert "system.info" in source
    assert "system.capabilities" in source
    assert "async_get_clientsession" not in source
    assert "requests" not in source
    assert "httpx" not in source
    assert "subprocess" not in source
    assert "provider" not in source
    assert "route" not in source.lower()
