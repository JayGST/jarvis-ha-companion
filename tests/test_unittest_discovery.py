"""Unittest discovery smoke tests for the Companion LLM boundary."""

from __future__ import annotations

import asyncio
import unittest

import tests.conftest  # noqa: F401
from homeassistant.helpers import llm

from custom_components.jarvis_ha_companion.llm import (
    GetRuntimeCapabilitiesTool,
    GetRuntimeInfoTool,
    GetRuntimeStatusTool,
)


class FakeClient:
    """Client that records capability calls."""

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


class RuntimeStatusToolDiscoveryTest(unittest.TestCase):
    """Ensure unittest discovery exercises the fixed runtime tool mapping."""

    def test_runtime_tools_fixed_mapping(self) -> None:
        client = FakeClient()
        tool_expectations = (
            (GetRuntimeStatusTool(client), "system.health"),
            (GetRuntimeInfoTool(client), "system.info"),
            (GetRuntimeCapabilitiesTool(client), "system.capabilities"),
        )

        for tool, capability in tool_expectations:
            with self.subTest(tool=tool.name):
                result = asyncio.run(
                    tool.async_call(
                        object(),
                        llm.ToolInput(
                            {"capability": "ignored", "parameters": {"x": 1}}
                        ),
                        llm.LLMContext(),
                    )
                )

                self.assertEqual(tool.parameters.schema, {})
                self.assertEqual(result["result"]["capability"], capability)

        self.assertEqual(
            client.calls,
            [
                ("system.health", {}),
                ("system.info", {}),
                ("system.capabilities", {}),
            ],
        )
