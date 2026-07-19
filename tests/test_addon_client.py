"""Tests for the JARVIS Add-on client boundary."""

from __future__ import annotations

import pytest

from custom_components.jarvis_ha_companion.addon_client import (
    IdentityPrompt,
    JarvisActivationAPIError,
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


class FakeHTTPResponse:
    def __init__(self, *, status: int, payload: object) -> None:
        self.status = status
        self.payload = payload
        self.raise_called = False

    def raise_for_status(self) -> None:
        self.raise_called = True

    async def json(self) -> object:
        return self.payload


class FakeHTTPSession:
    def __init__(self, response: FakeHTTPResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, str, object]] = []

    async def request(self, method: str, url: str, *, json: object = None) -> FakeHTTPResponse:
        self.calls.append((method, url, json))
        return self.response


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


@pytest.mark.asyncio
async def test_activation_client_methods_use_public_activation_paths() -> None:
    """Activation methods call the documented Project-JARVIS endpoints."""
    hass = type("Hass", (), {})()
    response = FakeHTTPResponse(
        status=202,
        payload={
            "success": True,
            "contract_version": 1,
            "result": {"activation": {"activation_id": "activation-1"}},
            "error": None,
        },
    )
    hass.data = {"session": FakeHTTPSession(response)}
    client = JarvisAddonClient(hass=hass, base_url="http://jarvis.local/")

    await client.get_activation("activation-1")
    await client.confirm_activation(
        activation_id="activation-1",
        confirmation_token="confirm-secret",
    )
    await client.retry_activation(
        activation_id="activation-1",
        retry_token="retry-secret",
    )
    await client.cancel_activation("activation-1")
    await client.get_activation_result("activation-1")

    assert hass.data["session"].calls == [
        ("GET", "http://jarvis.local/api/v1/activations/activation-1", None),
        (
            "POST",
            "http://jarvis.local/api/v1/activations/activation-1/confirm",
            {"contract_version": 1, "confirmation_token": "confirm-secret"},
        ),
        (
            "POST",
            "http://jarvis.local/api/v1/activations/activation-1/retry",
            {"contract_version": 1, "retry_token": "retry-secret"},
        ),
        (
            "POST",
            "http://jarvis.local/api/v1/activations/activation-1/cancel",
            {"contract_version": 1},
        ),
        ("GET", "http://jarvis.local/api/v1/activations/activation-1/result", None),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 403, 404, 409, 410, 503])
async def test_activation_client_normalizes_structured_api_errors(status: int) -> None:
    """Activation API errors retain status and stable code without exposing tokens."""
    hass = type("Hass", (), {})()
    response = FakeHTTPResponse(
        status=status,
        payload={
            "success": False,
            "contract_version": 1,
            "result": None,
            "error": {
                "code": "ACTIVATION_INVALID_STATE",
                "message": "Activation cannot be confirmed from its current state.",
            },
        },
    )
    hass.data = {"session": FakeHTTPSession(response)}
    client = JarvisAddonClient(hass=hass, base_url="http://jarvis.local")

    with pytest.raises(JarvisActivationAPIError) as error:
        await client.confirm_activation(
            activation_id="activation-1",
            confirmation_token="confirm-secret",
        )

    assert error.value.status == status
    assert error.value.code == "ACTIVATION_INVALID_STATE"
    assert "confirm-secret" not in str(error.value)


@pytest.mark.asyncio
async def test_activation_client_rejects_invalid_payload_shape() -> None:
    """Activation methods still validate JSON object responses."""
    hass = type("Hass", (), {})()
    hass.data = {"session": FakeHTTPSession(FakeHTTPResponse(status=200, payload=[]))}
    client = JarvisAddonClient(hass=hass, base_url="http://jarvis.local")

    with pytest.raises(JarvisAddonClientError):
        await client.get_activation("activation-1")
