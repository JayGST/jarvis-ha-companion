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
    ACTIVATIONS_PATH = "/api/v1/activations"
    REQUEST_TIMEOUT_SECONDS = 10
    ACTIVATION_STATUS_CODES = {200, 202, 400, 403, 404, 409, 410, 503}

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

        return await self._request_json(
            method="POST",
            path=self.EXECUTE_PATH,
            json_body=request,
            allowed_statuses={200},
            activation_request=False,
        )

    async def get_activation(self, activation_id: str) -> dict[str, Any]:
        """Fetch a safe public activation status snapshot."""
        return await self._request_json(
            method="GET",
            path=f"{self.ACTIVATIONS_PATH}/{activation_id}",
            allowed_statuses=self.ACTIVATION_STATUS_CODES,
            activation_request=True,
        )

    async def confirm_activation(
        self,
        *,
        activation_id: str,
        confirmation_token: str,
    ) -> dict[str, Any]:
        """Confirm a pending activation with its one-time credential."""
        return await self._request_json(
            method="POST",
            path=f"{self.ACTIVATIONS_PATH}/{activation_id}/confirm",
            json_body={
                "contract_version": self.CONTRACT_VERSION,
                "confirmation_token": confirmation_token,
            },
            allowed_statuses=self.ACTIVATION_STATUS_CODES,
            activation_request=True,
        )

    async def retry_activation(
        self,
        *,
        activation_id: str,
        retry_token: str,
    ) -> dict[str, Any]:
        """Accept a retry decision for a retry-waiting activation."""
        return await self._request_json(
            method="POST",
            path=f"{self.ACTIVATIONS_PATH}/{activation_id}/retry",
            json_body={
                "contract_version": self.CONTRACT_VERSION,
                "retry_token": retry_token,
            },
            allowed_statuses=self.ACTIVATION_STATUS_CODES,
            activation_request=True,
        )

    async def cancel_activation(self, activation_id: str) -> dict[str, Any]:
        """Cancel an activation before Project-JARVIS reaches the point of no return."""
        return await self._request_json(
            method="POST",
            path=f"{self.ACTIVATIONS_PATH}/{activation_id}/cancel",
            json_body={
                "contract_version": self.CONTRACT_VERSION,
            },
            allowed_statuses=self.ACTIVATION_STATUS_CODES,
            activation_request=True,
        )

    async def get_activation_result(self, activation_id: str) -> dict[str, Any]:
        """Fetch a retained completed capability result for an activation."""
        return await self._request_json(
            method="GET",
            path=f"{self.ACTIVATIONS_PATH}/{activation_id}/result",
            allowed_statuses=self.ACTIVATION_STATUS_CODES,
            activation_request=True,
        )

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

    async def _request_json(
        self,
        *,
        method: str,
        path: str,
        allowed_statuses: set[int],
        activation_request: bool,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session = async_get_clientsession(self._hass)

        try:
            async with asyncio.timeout(self.REQUEST_TIMEOUT_SECONDS):
                response = await session.request(
                    method,
                    f"{self._base_url}{path}",
                    json=json_body,
                )
                if response.status not in allowed_statuses:
                    response.raise_for_status()
                payload = await response.json()
        except TimeoutError as error:
            raise JarvisAddonClientError("Timed out calling JARVIS Add-on.") from error
        except ClientError as error:
            raise JarvisAddonClientError("Failed to call JARVIS Add-on.") from error

        if not isinstance(payload, dict):
            raise JarvisAddonClientError("JARVIS Add-on returned an invalid response.")

        if activation_request and payload.get("success") is False:
            error_payload = payload.get("error")
            code = None
            message = None

            if isinstance(error_payload, dict):
                raw_code = error_payload.get("code")
                raw_message = error_payload.get("message")
                code = raw_code if isinstance(raw_code, str) else None
                message = raw_message if isinstance(raw_message, str) else None

            raise JarvisActivationAPIError(
                status=response.status,
                code=code or "ACTIVATION_API_ERROR",
                message=message or "Activation API request failed.",
                payload=payload,
            )

        return payload


@dataclass(frozen=True)
class IdentityPrompt:
    """Canonical JARVIS identity prompt metadata returned by the Add-on."""

    prompt: str
    source: str | None = None
    content_sha256: str | None = None


class JarvisAddonClientError(Exception):
    """Raised when the JARVIS Add-on Capability API cannot be reached."""


class JarvisActivationAPIError(JarvisAddonClientError):
    """Raised for structured Activation API error responses."""

    def __init__(
        self,
        *,
        status: int,
        code: str,
        message: str,
        payload: dict[str, Any],
    ) -> None:
        self.status = status
        self.code = code
        self.payload = payload
        super().__init__(message)
