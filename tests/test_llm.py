"""Tests for the Home Assistant LLM API boundary."""

from __future__ import annotations

import pytest

from homeassistant.helpers import llm

from custom_components.jarvis_ha_companion.llm import (
    CAPABILITY_GUIDANCE,
    COMPANION_TOOL_INSTRUCTIONS,
    FALLBACK_IDENTITY_PROMPT,
    FindDecisionTool,
    GetIdeasTool,
    GetRoadmapItemsTool,
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

    assert inspect_result["result"]["capability"] == "inspect_project_module"
    assert capabilities_result["result"]["capability"] == "list_capabilities"
    assert extensions_result["result"]["capability"] == "list_extensions"
    assert ideas_result["result"]["capability"] == "get_ideas"
    assert roadmap_result["result"]["capability"] == "get_roadmap_items"
    assert decision_result["result"]["capability"] == "find_decision"
    assert client.calls == [
        ("inspect_project_module", {"module_name": "Windows Agent"}),
        ("list_capabilities", {}),
        ("list_extensions", {}),
        ("get_ideas", {}),
        ("get_roadmap_items", {}),
        ("find_decision", {}),
    ]
