"""Tests for memory-only activation workflow support."""

from __future__ import annotations

import json

import pytest

from custom_components.jarvis_ha_companion.activation import (
    ActivationLocalState,
    ActivationRegistry,
    ActivationWorkflow,
    PollingActivationStatusSource,
)
from custom_components.jarvis_ha_companion.addon_client import JarvisActivationAPIError


def activation_response(
    activation_id: str = "activation-1",
    status: str = "PENDING_CONFIRMATION",
    *,
    confirmation_token: str | None = "confirm-secret",
    retry_token: str | None = None,
    result_available: bool = False,
) -> dict[str, object]:
    result: dict[str, object] = {
        "owner": "WINDOWS_AGENT",
        "provider": "windows-agent",
        "activation_status": status,
        "activation_id": activation_id,
        "target_id": "main_pc",
        "capability_completed": status == "COMPLETED",
        "confirmation_required": status == "PENDING_CONFIRMATION",
        "retry_allowed": status == "WAITING_RETRY_CONFIRMATION",
        "cancellation_allowed": status
        in {"PENDING_CONFIRMATION", "WAITING_FOR_AGENT", "WAITING_RETRY_CONFIRMATION"},
        "result_available": result_available,
        "reason_code": "test",
    }

    if confirmation_token is not None:
        result["confirmation_token"] = confirmation_token

    if retry_token is not None:
        result["retry_token"] = retry_token

    return {
        "success": True,
        "contract_version": 1,
        "capability": "filesystem.read_file",
        "result": result,
    }


def status_payload(
    activation_id: str = "activation-1",
    status: str = "WAITING_FOR_AGENT",
    *,
    result_available: bool = False,
    failure_reason_code: str | None = None,
) -> dict[str, object]:
    return {
        "success": True,
        "contract_version": 1,
        "result": {
            "activation": {
                "activation_id": activation_id,
                "activation_status": status,
                "capability": "filesystem.read_file",
                "provider": "windows-agent",
                "target_id": "main_pc",
                "capability_completed": status == "COMPLETED",
                "capability_success": True if status == "COMPLETED" else None,
                "result_available": result_available,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:01Z",
                "completed_at": "2026-01-01T00:00:01Z"
                if status == "COMPLETED"
                else None,
                "confirmation_required": status == "PENDING_CONFIRMATION",
                "retry_allowed": status == "WAITING_RETRY_CONFIRMATION",
                "cancellation_allowed": status
                in {
                    "PENDING_CONFIRMATION",
                    "WAITING_FOR_AGENT",
                    "WAITING_RETRY_CONFIRMATION",
                },
                "reason_code": "test",
                "failure_reason_code": failure_reason_code,
            }
        },
        "error": None,
    }


class FakeClient:
    def __init__(self) -> None:
        self.statuses: list[dict[str, object]] = []
        self.confirm_payload = status_payload(status="WAITING_FOR_AGENT")
        self.retry_payload = status_payload(status="WAITING_FOR_AGENT")
        self.cancel_payload = status_payload(status="CANCELLED")
        self.result_payload = {
            "success": True,
            "contract_version": 1,
            "result": {
                "activation_id": "activation-1",
                "available": True,
                "completed": True,
                "capability_success": True,
                "result": {"success": True, "result": {"contents": "hello"}},
            },
            "error": None,
        }
        self.calls: list[tuple[str, object]] = []

    async def get_activation(self, activation_id: str) -> dict[str, object]:
        self.calls.append(("get", activation_id))
        return self.statuses.pop(0)

    async def confirm_activation(
        self,
        *,
        activation_id: str,
        confirmation_token: str,
    ) -> dict[str, object]:
        self.calls.append(("confirm", activation_id, confirmation_token))
        return self.confirm_payload

    async def retry_activation(
        self,
        *,
        activation_id: str,
        retry_token: str,
    ) -> dict[str, object]:
        self.calls.append(("retry", activation_id, retry_token))
        return self.retry_payload

    async def cancel_activation(self, activation_id: str) -> dict[str, object]:
        self.calls.append(("cancel", activation_id))
        return self.cancel_payload

    async def get_activation_result(self, activation_id: str) -> dict[str, object]:
        self.calls.append(("result", activation_id))
        return self.result_payload


@pytest.mark.asyncio
async def test_pending_confirmation_is_registered_without_exposing_token() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    workflow = ActivationWorkflow(client=client, registry=registry)

    result = await workflow.observe_capability_response(
        activation_response(),
        conversation_context_id="conversation-1",
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )
    entry = registry.get("activation-1")

    assert entry is not None
    assert entry.confirmation_token == "confirm-secret"
    assert entry.conversation_context_id == "conversation-1"
    assert entry.local_workflow_state == ActivationLocalState.AWAITING_CONFIRMATION
    assert result["message"] == "This requires waking your PC. Should I continue?"
    assert "confirm-secret" not in json.dumps(result)


@pytest.mark.asyncio
async def test_confirm_consumes_token_and_fetches_result_once() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    client.statuses = [
        status_payload(status="COMPLETED", result_available=True),
        status_payload(status="COMPLETED", result_available=True),
    ]
    workflow = ActivationWorkflow(client=client, registry=registry)
    registry.upsert_from_capability_response(
        activation_response(),
        conversation_context_id=None,
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )

    result = await workflow.confirm("activation-1")
    second = await workflow.get_status("activation-1")
    entry = registry.get("activation-1")

    assert entry is not None
    assert entry.confirmation_token is None
    assert entry.result_fetched is True
    assert result["activation_result"]["result"]["result"]["contents"] == "hello"
    assert second["result_fetched"] is True
    assert client.calls.count(("result", "activation-1")) == 1
    assert ("confirm", "activation-1", "confirm-secret") in client.calls


@pytest.mark.asyncio
async def test_lost_confirmation_response_recovers_with_status_on_conflict() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    client.statuses = [status_payload(status="WAITING_FOR_AGENT")]

    async def conflict_confirm(**kwargs: object) -> dict[str, object]:
        raise JarvisActivationAPIError(
            status=409,
            code="ACTIVATION_INVALID_STATE",
            message="Activation cannot be confirmed from its current state.",
            payload={},
        )

    client.confirm_activation = conflict_confirm
    workflow = ActivationWorkflow(client=client, registry=registry)
    registry.upsert_from_capability_response(
        activation_response(),
        conversation_context_id=None,
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )

    result = await workflow.confirm("activation-1")
    entry = registry.get("activation-1")

    assert result["state"] == "WAITING_FOR_AGENT"
    assert entry is not None
    assert entry.confirmation_token is None


@pytest.mark.asyncio
async def test_retry_uses_stored_retry_token_and_then_removes_it() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    client.statuses = [status_payload(status="COMPLETED")]
    workflow = ActivationWorkflow(client=client, registry=registry)
    registry.upsert_from_capability_response(
        activation_response(
            status="WAITING_RETRY_CONFIRMATION",
            confirmation_token=None,
            retry_token="retry-secret",
        ),
        conversation_context_id=None,
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )

    await workflow.retry("activation-1")
    entry = registry.get("activation-1")

    assert entry is not None
    assert entry.retry_token is None
    assert ("retry", "activation-1", "retry-secret") in client.calls


@pytest.mark.asyncio
async def test_retry_without_token_fails_locally() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    workflow = ActivationWorkflow(client=client, registry=registry)
    registry.upsert_from_capability_response(
        activation_response(
            status="WAITING_RETRY_CONFIRMATION",
            confirmation_token=None,
            retry_token=None,
        ),
        conversation_context_id=None,
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )

    result = await workflow.retry("activation-1")

    assert result["success"] is False
    assert result["error"]["code"] == "ACTIVATION_RETRY_TOKEN_UNAVAILABLE"
    assert client.calls == []


@pytest.mark.asyncio
async def test_retry_conflict_recovers_status_and_removes_stale_token() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    client.statuses = [status_payload(status="WAITING_FOR_AGENT")]

    async def conflict_retry(**kwargs: object) -> dict[str, object]:
        raise JarvisActivationAPIError(
            status=409,
            code="ACTIVATION_INVALID_STATE",
            message="Activation cannot be retried from its current state.",
            payload={},
        )

    client.retry_activation = conflict_retry
    workflow = ActivationWorkflow(client=client, registry=registry)
    registry.upsert_from_capability_response(
        activation_response(
            status="WAITING_RETRY_CONFIRMATION",
            confirmation_token=None,
            retry_token="retry-secret",
        ),
        conversation_context_id=None,
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )

    result = await workflow.retry("activation-1")
    entry = registry.get("activation-1")

    assert result["state"] == "WAITING_FOR_AGENT"
    assert entry is not None
    assert entry.retry_token is None


@pytest.mark.asyncio
async def test_cancel_removes_tokens_and_keeps_terminal_summary() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    workflow = ActivationWorkflow(client=client, registry=registry)
    registry.upsert_from_capability_response(
        activation_response(
            status="WAITING_RETRY_CONFIRMATION",
            retry_token="retry-secret",
        ),
        conversation_context_id=None,
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )

    result = await workflow.cancel("activation-1")
    entry = registry.get("activation-1")

    assert entry is not None
    assert entry.confirmation_token is None
    assert entry.retry_token is None
    assert result["state"] == "CANCELLED"


@pytest.mark.asyncio
async def test_multiple_activations_are_tracked_independently() -> None:
    registry = ActivationRegistry()

    first = registry.upsert_from_capability_response(
        activation_response("activation-1"),
        conversation_context_id="conversation-1",
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )
    second = registry.upsert_from_capability_response(
        activation_response("activation-2", confirmation_token="confirm-secret-2"),
        conversation_context_id="conversation-1",
        capability_name="system.metrics",
        user_facing_summary="Get metrics",
    )

    pending = registry.pending_confirmations()

    assert first is not None
    assert second is not None
    assert {entry.activation_id for entry in pending} == {
        "activation-1",
        "activation-2",
    }
    assert first.confirmation_token == "confirm-secret"
    assert second.confirmation_token == "confirm-secret-2"


@pytest.mark.asyncio
async def test_follow_up_status_uses_single_active_activation() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    client.statuses = [status_payload(status="WAITING_FOR_AGENT")]
    workflow = ActivationWorkflow(client=client, registry=registry)
    registry.upsert_from_capability_response(
        activation_response(status="WAITING_FOR_AGENT", confirmation_token=None),
        conversation_context_id="conversation-1",
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )

    result = await workflow.get_follow_up_status(
        conversation_context_id="conversation-1"
    )

    assert result["status"] == "starting"
    assert result["message"] == "The PC is still starting."
    assert client.calls == [("get", "activation-1")]


@pytest.mark.asyncio
async def test_follow_up_status_prefers_same_conversation_context() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    client.statuses = [status_payload("activation-2", "EXECUTING_CAPABILITY")]
    workflow = ActivationWorkflow(client=client, registry=registry)
    registry.upsert_from_capability_response(
        activation_response("activation-1", "WAITING_FOR_AGENT", confirmation_token=None),
        conversation_context_id="conversation-1",
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )
    registry.upsert_from_capability_response(
        activation_response("activation-2", "WAITING_FOR_AGENT", confirmation_token=None),
        conversation_context_id="conversation-2",
        capability_name="system.metrics",
        user_facing_summary="Get system metrics",
    )

    result = await workflow.get_follow_up_status(
        conversation_context_id="conversation-2"
    )

    assert result["summary"] == "Get system metrics"
    assert result["status"] == "executing"
    assert client.calls == [("get", "activation-2")]


@pytest.mark.asyncio
async def test_follow_up_status_asks_when_multiple_same_context_match() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    workflow = ActivationWorkflow(client=client, registry=registry)
    registry.upsert_from_capability_response(
        activation_response("activation-1", "WAITING_FOR_AGENT", confirmation_token=None),
        conversation_context_id="conversation-1",
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )
    registry.upsert_from_capability_response(
        activation_response("activation-2", "WAITING_FOR_AGENT", confirmation_token=None),
        conversation_context_id="conversation-1",
        capability_name="system.metrics",
        user_facing_summary="Get system metrics",
    )

    result = await workflow.get_follow_up_status(
        conversation_context_id="conversation-1"
    )

    assert result["status"] == "needs_clarification"
    assert {choice["summary"] for choice in result["choices"]} == {
        "Read README.md",
        "Get system metrics",
    }
    assert client.calls == []


@pytest.mark.asyncio
async def test_follow_up_status_uses_summary_hint_to_select_activation() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    client.statuses = [status_payload("activation-2", "WAITING_FOR_AGENT")]
    workflow = ActivationWorkflow(client=client, registry=registry)
    registry.upsert_from_capability_response(
        activation_response("activation-1", "WAITING_FOR_AGENT", confirmation_token=None),
        conversation_context_id="conversation-1",
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )
    registry.upsert_from_capability_response(
        activation_response("activation-2", "WAITING_FOR_AGENT", confirmation_token=None),
        conversation_context_id="conversation-1",
        capability_name="system.metrics",
        user_facing_summary="Get system metrics",
    )

    result = await workflow.get_follow_up_status(
        conversation_context_id="conversation-1",
        summary_hint="metrics",
    )

    assert result["summary"] == "Get system metrics"
    assert client.calls == [("get", "activation-2")]


@pytest.mark.asyncio
async def test_follow_up_status_summarizes_all_active_activations() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    client.statuses = [
        status_payload("activation-1", "WAITING_FOR_AGENT"),
        status_payload("activation-2", "EXECUTING_CAPABILITY"),
    ]
    workflow = ActivationWorkflow(client=client, registry=registry)
    registry.upsert_from_capability_response(
        activation_response("activation-1", "WAITING_FOR_AGENT", confirmation_token=None),
        conversation_context_id="conversation-1",
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )
    registry.upsert_from_capability_response(
        activation_response("activation-2", "WAITING_FOR_AGENT", confirmation_token=None),
        conversation_context_id="conversation-2",
        capability_name="system.metrics",
        user_facing_summary="Get system metrics",
    )

    result = await workflow.get_follow_up_status(include_all=True)

    assert result["status"] == "multiple"
    assert [item["status"] for item in result["activations"]] == [
        "starting",
        "executing",
    ]


@pytest.mark.asyncio
async def test_follow_up_status_returns_no_active_activation() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    workflow = ActivationWorkflow(client=client, registry=registry)

    result = await workflow.get_follow_up_status(
        conversation_context_id="conversation-1"
    )

    assert result == {
        "success": True,
        "status": "none",
        "message": "No pending activation is currently being tracked.",
        "activations": [],
    }


@pytest.mark.asyncio
async def test_follow_up_status_fetches_completed_result_once_and_reuses_cache() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    client.statuses = [
        status_payload(status="COMPLETED", result_available=True),
        status_payload(status="COMPLETED", result_available=True),
    ]
    workflow = ActivationWorkflow(client=client, registry=registry)
    registry.upsert_from_capability_response(
        activation_response(status="WAITING_FOR_AGENT", confirmation_token=None),
        conversation_context_id="conversation-1",
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )

    first = await workflow.get_follow_up_status(
        conversation_context_id="conversation-1"
    )
    second = await workflow.get_follow_up_status(
        conversation_context_id="conversation-1"
    )

    assert first["activation_result"]["result"]["result"]["contents"] == "hello"
    assert second["result_fetched"] is True
    assert client.calls.count(("result", "activation-1")) == 1


@pytest.mark.asyncio
async def test_follow_up_status_reports_failure_reason_code_only() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    client.statuses = [
        status_payload(
            status="FAILED",
            failure_reason_code="PROVIDER_START_TIMEOUT",
        )
    ]
    workflow = ActivationWorkflow(client=client, registry=registry)
    registry.upsert_from_capability_response(
        activation_response(status="WAITING_FOR_AGENT", confirmation_token=None),
        conversation_context_id="conversation-1",
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )

    result = await workflow.get_follow_up_status(
        conversation_context_id="conversation-1"
    )

    assert result["status"] == "failed"
    assert result["message"] == (
        "The requested task failed. Reason code: PROVIDER_START_TIMEOUT."
    )


@pytest.mark.asyncio
async def test_follow_up_status_reports_retry_waiting_without_token_gracefully() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    client.statuses = [status_payload(status="WAITING_RETRY_CONFIRMATION")]
    workflow = ActivationWorkflow(client=client, registry=registry)
    registry.upsert_from_capability_response(
        activation_response(status="WAITING_FOR_AGENT", confirmation_token=None),
        conversation_context_id="conversation-1",
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )

    result = await workflow.get_follow_up_status(
        conversation_context_id="conversation-1"
    )

    assert result["status"] == "waiting_for_retry_confirmation"
    assert "cannot currently be initiated automatically" in result["message"]


@pytest.mark.asyncio
async def test_cancel_follow_up_resolves_single_active_activation() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    workflow = ActivationWorkflow(client=client, registry=registry)
    registry.upsert_from_capability_response(
        activation_response(status="WAITING_FOR_AGENT", confirmation_token=None),
        conversation_context_id="conversation-1",
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )

    result = await workflow.cancel_follow_up(conversation_context_id="conversation-1")

    assert result["status"] == "cancelled"
    assert client.calls == [("cancel", "activation-1")]


@pytest.mark.asyncio
async def test_confirm_follow_up_resolves_single_pending_confirmation() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    client.statuses = [status_payload(status="COMPLETED")]
    workflow = ActivationWorkflow(client=client, registry=registry)
    registry.upsert_from_capability_response(
        activation_response(),
        conversation_context_id="conversation-1",
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )

    result = await workflow.confirm_follow_up(conversation_context_id="conversation-1")

    assert result["status"] == "completed"
    assert ("confirm", "activation-1", "confirm-secret") in client.calls


@pytest.mark.asyncio
async def test_retry_follow_up_reports_unavailable_token_gracefully() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    workflow = ActivationWorkflow(client=client, registry=registry)
    registry.upsert_from_capability_response(
        activation_response(
            status="WAITING_RETRY_CONFIRMATION",
            confirmation_token=None,
        ),
        conversation_context_id="conversation-1",
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )

    result = await workflow.retry_follow_up(conversation_context_id="conversation-1")

    assert result["success"] is False
    assert result["error"]["code"] == "ACTIVATION_RETRY_TOKEN_UNAVAILABLE"


@pytest.mark.asyncio
async def test_polling_uses_two_second_then_five_second_schedule() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    clock_value = 0.0
    sleeps: list[float] = []

    def clock() -> float:
        return clock_value

    async def sleeper(delay: float) -> None:
        nonlocal clock_value
        sleeps.append(delay)
        clock_value += delay

    client.statuses = [
        status_payload(status="WAITING_FOR_AGENT"),
        *[status_payload(status="WAITING_FOR_AGENT") for _ in range(15)],
        status_payload(status="COMPLETED"),
    ]
    source = PollingActivationStatusSource(
        client=client,
        registry=registry,
        sleeper=sleeper,
        monotonic=clock,
        timeout_seconds=120,
    )

    entry = await source.poll_until_stable("activation-1")

    assert entry is not None
    assert entry.status == "COMPLETED"
    assert sleeps[:15] == [2.0] * 15
    assert sleeps[15:] == [5.0]


@pytest.mark.asyncio
async def test_poll_timeout_does_not_mark_activation_failed() -> None:
    registry = ActivationRegistry()
    client = FakeClient()
    clock_value = 0.0

    def clock() -> float:
        return clock_value

    async def sleeper(delay: float) -> None:
        nonlocal clock_value
        clock_value += delay

    client.statuses = [
        status_payload(status="WAITING_FOR_AGENT"),
        status_payload(status="WAITING_FOR_AGENT"),
        status_payload(status="WAITING_FOR_AGENT"),
    ]
    source = PollingActivationStatusSource(
        client=client,
        registry=registry,
        sleeper=sleeper,
        monotonic=clock,
        timeout_seconds=3,
    )

    entry = await source.poll_until_stable("activation-1")

    assert entry is not None
    assert entry.status == "WAITING_FOR_AGENT"
    assert entry.local_workflow_state == ActivationLocalState.POLLING


def test_lazy_cleanup_removes_expired_terminal_entries_only() -> None:
    clock_value = 0.0
    registry = ActivationRegistry(
        terminal_retention_seconds=10,
        clock=lambda: clock_value,
    )
    registry.update_from_activation_payload(status_payload(status="COMPLETED"))
    registry.update_from_activation_payload(status_payload("activation-2", "WAITING_FOR_AGENT"))
    clock_value = 11.0

    assert registry.get("activation-1") is None
    assert registry.get("activation-2") is not None


def test_lazy_cleanup_removes_stale_retry_waiting_entries() -> None:
    clock_value = 0.0
    registry = ActivationRegistry(
        terminal_retention_seconds=10,
        clock=lambda: clock_value,
    )
    registry.upsert_from_capability_response(
        activation_response(
            status="WAITING_RETRY_CONFIRMATION",
            confirmation_token=None,
            retry_token="retry-secret",
        ),
        conversation_context_id=None,
        capability_name="filesystem.read_file",
        user_facing_summary="Read README.md",
    )
    clock_value = 11.0

    assert registry.get("activation-1") is None
