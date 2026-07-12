"""Client boundary for the JARVIS Add-on Capability API."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession


class JarvisAddonClient:
    """Minimal async HTTP client for the JARVIS Add-on Capability API."""

    CONTRACT_VERSION = 1
    EXECUTE_PATH = "/api/v1/capabilities/execute"
    REQUEST_TIMEOUT_SECONDS = 10

    def __init__(
        self,
        hass: HomeAssistant,
        base_url: str,
    ) -> None:
        self._hass = hass
        self._base_url = base_url.rstrip("/")

    async def execute_capability(
        self,
        *,
        capability: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a JARVIS Add-on capability and return its structured response."""
        request = {
            "contract_version": self.CONTRACT_VERSION,
            "capability": capability,
            "parameters": parameters,
        }

        session = async_get_clientsession(self._hass)

        try:
            async with asyncio.timeout(self.REQUEST_TIMEOUT_SECONDS):
                response = await session.post(
                    f"{self._base_url}{self.EXECUTE_PATH}",
                    json=request,
                )
                response.raise_for_status()
                payload = await response.json()
        except TimeoutError as error:
            raise JarvisAddonClientError("Timed out calling JARVIS Add-on.") from error
        except ClientError as error:
            raise JarvisAddonClientError("Failed to call JARVIS Add-on.") from error

        if not isinstance(payload, dict):
            raise JarvisAddonClientError("JARVIS Add-on returned an invalid response.")

        return payload

    async def get_identity_prompt(self) -> IdentityPrompt:
        """Fetch the canonical runtime JARVIS identity prompt from the Add-on."""
        payload = await self.execute_capability(
            capability="get_identity_prompt",
            parameters={},
        )

        result = payload.get("result")

        if not isinstance(result, dict):
            raise JarvisAddonClientError(
                "JARVIS Add-on returned an invalid identity response."
            )

        prompt = result.get("prompt")
        source = result.get("source")
        content_sha256 = result.get("content_sha256")

        if not isinstance(prompt, str) or not prompt.strip():
            raise JarvisAddonClientError(
                "JARVIS Add-on returned an invalid identity prompt."
            )

        return IdentityPrompt(
            prompt=prompt,
            source=source if isinstance(source, str) else None,
            content_sha256=content_sha256
            if isinstance(content_sha256, str)
            else None,
        )


@dataclass(frozen=True)
class IdentityPrompt:
    """Canonical JARVIS identity prompt metadata returned by the Add-on."""

    prompt: str
    source: str | None = None
    content_sha256: str | None = None


class JarvisAddonClientError(Exception):
    """Raised when the JARVIS Add-on Capability API cannot be reached."""
