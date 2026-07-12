"""Tests for the JARVIS Add-on client boundary."""

from __future__ import annotations

import pytest

from custom_components.jarvis_ha_companion.addon_client import (
    IdentityPrompt,
    JarvisAddonClient,
    JarvisAddonClientError,
)


class FakeClient(JarvisAddonClient):
    """Client with the HTTP transport replaced by an in-memory response."""

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def execute_capability(
        self,
        *,
        capability: str,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        self.calls.append((capability, parameters))
        return self.payload


@pytest.mark.asyncio
async def test_get_identity_prompt_parses_capability_result() -> None:
    """The identity prompt comes from the standard Capability API result."""
    client = FakeClient(
        {
            "result": {
                "prompt": "Canonical runtime identity.",
                "source": "docs/identity/JARVIS_IDENTITY.md",
                "content_sha256": "abc123",
            }
        }
    )

    identity = await client.get_identity_prompt()

    assert identity == IdentityPrompt(
        prompt="Canonical runtime identity.",
        source="docs/identity/JARVIS_IDENTITY.md",
        content_sha256="abc123",
    )
    assert client.calls == [("get_identity_prompt", {})]


@pytest.mark.asyncio
async def test_get_identity_prompt_rejects_invalid_result() -> None:
    """Invalid identity responses fail at the client boundary."""
    client = FakeClient({"result": {"prompt": ""}})

    with pytest.raises(JarvisAddonClientError):
        await client.get_identity_prompt()
