"""Memory-only Companion activation workflow support."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Protocol

from .addon_client import JarvisActivationAPIError, JarvisAddonClient


class ActivationLocalState(str, Enum):
    """Companion-local activation conversation state."""

    IDLE = "IDLE"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    CONFIRMING = "CONFIRMING"
    POLLING = "POLLING"
    AWAITING_RETRY = "AWAITING_RETRY"
    RETRYING = "RETRYING"
    CANCELLING = "CANCELLING"
    FETCHING_RESULT = "FETCHING_RESULT"
    DONE = "DONE"


POLL_TERMINAL_STATUSES = {
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    "PENDING_CONFIRMATION",
    "WAITING_RETRY_CONFIRMATION",
}


ACTIVE_LOCAL_STATES = {
    ActivationLocalState.AWAITING_CONFIRMATION,
    ActivationLocalState.CONFIRMING,
    ActivationLocalState.POLLING,
    ActivationLocalState.AWAITING_RETRY,
    ActivationLocalState.RETRYING,
    ActivationLocalState.CANCELLING,
    ActivationLocalState.FETCHING_RESULT,
}


@dataclass
class ActivationEntry:
    """Tracked activation state retained only in Home Assistant memory."""

    activation_id: str
    conversation_context_id: str | None
    capability_name: str
    user_facing_summary: str
    confirmation_token: str | None = field(default=None, repr=False)
    retry_token: str | None = field(default=None, repr=False)
    latest_activation_snapshot: dict[str, Any] = field(default_factory=dict)
    local_workflow_state: ActivationLocalState = ActivationLocalState.IDLE
    result_fetched: bool = False
    result_payload: dict[str, Any] | None = None
    created_at: float = field(default_factory=time.monotonic)
    last_update_at: float = field(default_factory=time.monotonic)

    def update_snapshot(self, snapshot: dict[str, Any], *, now: float) -> None:
        """Store the latest public activation snapshot."""
        self.latest_activation_snapshot = dict(snapshot)
        self.last_update_at = now

        status = snapshot.get("activation_status")

        if status == "PENDING_CONFIRMATION":
            self.local_workflow_state = ActivationLocalState.AWAITING_CONFIRMATION
        elif status == "WAITING_RETRY_CONFIRMATION":
            self.local_workflow_state = ActivationLocalState.AWAITING_RETRY
        elif status in {"COMPLETED", "FAILED", "CANCELLED"}:
            self.local_workflow_state = ActivationLocalState.DONE
        elif status in {"WAITING_FOR_AGENT", "EXECUTING_CAPABILITY"}:
            self.local_workflow_state = ActivationLocalState.POLLING

    @property
    def status(self) -> str | None:
        status = self.latest_activation_snapshot.get("activation_status")
        return status if isinstance(status, str) else None


class ActivationRegistry:
    """Memory-only activation registry keyed by activation_id."""

    def __init__(
        self,
        *,
        terminal_retention_seconds: float = 900.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._entries: dict[str, ActivationEntry] = {}
        self._terminal_retention_seconds = terminal_retention_seconds
        self._clock = clock

    def upsert_from_capability_response(
        self,
        response: dict[str, Any],
        *,
        conversation_context_id: str | None,
        capability_name: str,
        user_facing_summary: str,
    ) -> ActivationEntry | None:
        """Track an activation returned by a Capability API response."""
        result = response.get("result")

        if not isinstance(result, dict):
            return None

        activation_id = result.get("activation_id")
        activation_status = result.get("activation_status")

        if not isinstance(activation_id, str) or not isinstance(activation_status, str):
            return None

        snapshot = {
            key: value
            for key, value in result.items()
            if key not in {"confirmation_token", "retry_token"}
        }
        snapshot.setdefault("capability", response.get("capability", capability_name))

        now = self._clock()
        entry = self._entries.get(activation_id)

        if entry is None:
            entry = ActivationEntry(
                activation_id=activation_id,
                conversation_context_id=conversation_context_id,
                capability_name=capability_name,
                user_facing_summary=user_facing_summary,
                created_at=now,
                last_update_at=now,
            )
            self._entries[activation_id] = entry

        confirmation_token = result.get("confirmation_token")
        retry_token = result.get("retry_token")

        if isinstance(confirmation_token, str) and confirmation_token:
            entry.confirmation_token = confirmation_token

        if isinstance(retry_token, str) and retry_token:
            entry.retry_token = retry_token

        entry.update_snapshot(snapshot, now=now)
        self.cleanup()
        return entry

    def update_from_activation_payload(self, payload: dict[str, Any]) -> ActivationEntry:
        """Update an existing entry from an Activation API payload."""
        snapshot = extract_activation_snapshot(payload)
        activation_id = snapshot["activation_id"]
        now = self._clock()
        entry = self._entries.get(activation_id)

        if entry is None:
            entry = ActivationEntry(
                activation_id=activation_id,
                conversation_context_id=None,
                capability_name=str(snapshot.get("capability", "")),
                user_facing_summary=str(snapshot.get("capability", "activation")),
                created_at=now,
                last_update_at=now,
            )
            self._entries[activation_id] = entry

        entry.update_snapshot(snapshot, now=now)
        self.cleanup()
        return entry

    def get(self, activation_id: str) -> ActivationEntry | None:
        """Return one tracked activation entry."""
        self.cleanup()
        return self._entries.get(activation_id)

    def all(self) -> list[ActivationEntry]:
        """Return all currently retained entries."""
        self.cleanup()
        return list(self._entries.values())

    def pending_confirmations(self) -> list[ActivationEntry]:
        """Return pending confirmation entries."""
        return [
            entry
            for entry in self.all()
            if entry.local_workflow_state == ActivationLocalState.AWAITING_CONFIRMATION
        ]

    def active_entries(
        self,
        *,
        conversation_context_id: str | None = None,
    ) -> list[ActivationEntry]:
        """Return active entries, optionally scoped to one conversation context."""
        return [
            entry
            for entry in self.all()
            if entry.local_workflow_state in ACTIVE_LOCAL_STATES
            and (
                conversation_context_id is None
                or entry.conversation_context_id == conversation_context_id
            )
        ]

    def retained_terminal_entries(
        self,
        *,
        conversation_context_id: str | None = None,
    ) -> list[ActivationEntry]:
        """Return recently retained terminal entries."""
        return [
            entry
            for entry in self.all()
            if entry.local_workflow_state == ActivationLocalState.DONE
            and (
                conversation_context_id is None
                or entry.conversation_context_id == conversation_context_id
            )
        ]

    def remove_confirmation_token(self, activation_id: str) -> None:
        """Remove a consumed confirmation token immediately."""
        entry = self._entries.get(activation_id)

        if entry is not None:
            entry.confirmation_token = None
            entry.last_update_at = self._clock()

    def remove_retry_token(self, activation_id: str) -> None:
        """Remove a consumed retry token immediately."""
        entry = self._entries.get(activation_id)

        if entry is not None:
            entry.retry_token = None
            entry.last_update_at = self._clock()

    def cleanup(self) -> None:
        """Remove expired terminal and stale actionable activation summaries lazily."""
        now = self._clock()

        for activation_id, entry in list(self._entries.items()):
            if entry.local_workflow_state not in {
                ActivationLocalState.AWAITING_CONFIRMATION,
                ActivationLocalState.AWAITING_RETRY,
                ActivationLocalState.DONE,
            }:
                continue

            if now - entry.last_update_at > self._terminal_retention_seconds:
                self._entries.pop(activation_id, None)


class ActivationStatusSource(Protocol):
    """Activation status observation boundary."""

    async def poll_until_stable(self, activation_id: str) -> ActivationEntry | None:
        """Poll an activation until it reaches a client-stable state."""


class PollingActivationStatusSource:
    """Polls Project-JARVIS Activation API without blocking the event loop."""

    def __init__(
        self,
        *,
        client: JarvisAddonClient,
        registry: ActivationRegistry,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        timeout_seconds: float = 90.0,
    ) -> None:
        self._client = client
        self._registry = registry
        self._sleeper = sleeper
        self._monotonic = monotonic
        self._timeout_seconds = timeout_seconds

    async def poll_until_stable(self, activation_id: str) -> ActivationEntry | None:
        """Poll status until terminal/actionable state or local timeout."""
        started_at = self._monotonic()

        while True:
            payload = await self._client.get_activation(activation_id)
            entry = self._registry.update_from_activation_payload(payload)
            status = entry.status

            if status in POLL_TERMINAL_STATUSES:
                return entry

            elapsed = self._monotonic() - started_at

            if elapsed >= self._timeout_seconds:
                return entry

            await self._sleeper(2.0 if elapsed < 30.0 else 5.0)


class ActivationWorkflow:
    """Coordinates Companion activation registry, polling and user actions."""

    def __init__(
        self,
        *,
        client: JarvisAddonClient,
        registry: ActivationRegistry,
        status_source: ActivationStatusSource | None = None,
    ) -> None:
        self._client = client
        self._registry = registry
        self._status_source = status_source or PollingActivationStatusSource(
            client=client,
            registry=registry,
        )

    async def observe_capability_response(
        self,
        response: dict[str, Any],
        *,
        conversation_context_id: str | None,
        capability_name: str,
        user_facing_summary: str,
    ) -> dict[str, Any]:
        """Store activation responses and return Claude-facing guidance."""
        entry = self._registry.upsert_from_capability_response(
            response,
            conversation_context_id=conversation_context_id,
            capability_name=capability_name,
            user_facing_summary=user_facing_summary,
        )

        if entry is None:
            return response

        if entry.status == "PENDING_CONFIRMATION":
            return activation_prompt_response(
                entry,
                message="This requires waking your PC. Should I continue?",
            )

        if entry.status == "ACTIVATION_STARTED":
            polled_entry = await self._status_source.poll_until_stable(
                entry.activation_id
            )
            return await self._result_or_status(polled_entry or entry)

        return activation_prompt_response(entry)

    async def get_status(self, activation_id: str) -> dict[str, Any]:
        """Fetch the latest activation status and any completed result."""
        payload = await self._client.get_activation(activation_id)
        entry = self._registry.update_from_activation_payload(payload)
        return await self._result_or_status(entry)

    async def get_follow_up_status(
        self,
        *,
        activation_id: str | None = None,
        conversation_context_id: str | None = None,
        summary_hint: str | None = None,
        include_all: bool = False,
    ) -> dict[str, Any]:
        """Resolve a natural follow-up status request without exposing activation IDs."""
        if activation_id:
            return await self.get_status(activation_id)

        active_entries = self._candidate_entries(
            conversation_context_id=conversation_context_id,
        )

        if include_all:
            if not active_entries:
                return no_activation_response()

            return await self._summarize_entries(active_entries)

        if summary_hint:
            hinted_entries = _entries_matching_summary(active_entries, summary_hint)

            if len(hinted_entries) == 1:
                return await self.get_status(hinted_entries[0].activation_id)

            if len(hinted_entries) > 1:
                return clarification_response(hinted_entries)

        if len(active_entries) == 1:
            return await self.get_status(active_entries[0].activation_id)

        if len(active_entries) > 1:
            same_context = (
                self._registry.active_entries(
                    conversation_context_id=conversation_context_id,
                )
                if conversation_context_id is not None
                else []
            )

            if len(same_context) == 1:
                return await self.get_status(same_context[0].activation_id)

            if len(same_context) > 1:
                return clarification_response(same_context)

            return clarification_response(active_entries)

        retained = self._registry.retained_terminal_entries(
            conversation_context_id=conversation_context_id,
        )

        if summary_hint:
            retained = _entries_matching_summary(retained, summary_hint)

        if len(retained) == 1:
            return await self.get_status(retained[0].activation_id)

        if len(retained) > 1:
            return await self._summarize_entries(retained)

        return no_activation_response()

    async def confirm(self, activation_id: str) -> dict[str, Any]:
        """Confirm a pending activation and resume polling."""
        entry = require_entry(self._registry, activation_id)

        if entry.confirmation_token is None:
            return await self.get_status(activation_id)

        entry.local_workflow_state = ActivationLocalState.CONFIRMING

        try:
            payload = await self._client.confirm_activation(
                activation_id=activation_id,
                confirmation_token=entry.confirmation_token,
            )
        except JarvisActivationAPIError as error:
            if error.status == 409:
                result = await self.get_status(activation_id)
                refreshed = self._registry.get(activation_id)

                if refreshed is not None and refreshed.status != "PENDING_CONFIRMATION":
                    self._registry.remove_confirmation_token(activation_id)

                return result
            raise

        self._registry.remove_confirmation_token(activation_id)
        entry = self._registry.update_from_activation_payload(payload)
        polled_entry = await self._status_source.poll_until_stable(activation_id)
        return await self._result_or_status(polled_entry or entry)

    async def confirm_follow_up(
        self,
        *,
        activation_id: str | None = None,
        conversation_context_id: str | None = None,
        summary_hint: str | None = None,
    ) -> dict[str, Any]:
        """Resolve and confirm a natural follow-up approval."""
        if activation_id:
            return await self.confirm(activation_id)

        entries = [
            entry
            for entry in self._candidate_entries(
                conversation_context_id=conversation_context_id,
            )
            if entry.local_workflow_state == ActivationLocalState.AWAITING_CONFIRMATION
        ]

        if summary_hint:
            entries = _entries_matching_summary(entries, summary_hint)

        if len(entries) == 1:
            return await self.confirm(entries[0].activation_id)

        if len(entries) > 1:
            return clarification_response(entries)

        return no_activation_response()

    async def retry(self, activation_id: str) -> dict[str, Any]:
        """Retry a retry-waiting activation and resume polling."""
        entry = require_entry(self._registry, activation_id)

        if entry.retry_token is None:
            return {
                "success": False,
                "activation_id": activation_id,
                "error": {
                    "code": "ACTIVATION_RETRY_TOKEN_UNAVAILABLE",
                    "message": "Activation retry token is unavailable.",
                },
            }

        entry.local_workflow_state = ActivationLocalState.RETRYING

        try:
            payload = await self._client.retry_activation(
                activation_id=activation_id,
                retry_token=entry.retry_token,
            )
        except JarvisActivationAPIError as error:
            if error.status == 409:
                result = await self.get_status(activation_id)
                refreshed = self._registry.get(activation_id)

                if (
                    refreshed is not None
                    and refreshed.status != "WAITING_RETRY_CONFIRMATION"
                ):
                    self._registry.remove_retry_token(activation_id)

                return result
            raise

        self._registry.remove_retry_token(activation_id)
        entry = self._registry.update_from_activation_payload(payload)
        polled_entry = await self._status_source.poll_until_stable(activation_id)
        return await self._result_or_status(polled_entry or entry)

    async def retry_follow_up(
        self,
        *,
        activation_id: str | None = None,
        conversation_context_id: str | None = None,
        summary_hint: str | None = None,
    ) -> dict[str, Any]:
        """Resolve and retry a natural follow-up retry approval."""
        if activation_id:
            return await self.retry(activation_id)

        entries = [
            entry
            for entry in self._candidate_entries(
                conversation_context_id=conversation_context_id,
            )
            if entry.local_workflow_state == ActivationLocalState.AWAITING_RETRY
        ]

        if summary_hint:
            entries = _entries_matching_summary(entries, summary_hint)

        if len(entries) == 1:
            return await self.retry(entries[0].activation_id)

        if len(entries) > 1:
            return clarification_response(entries)

        return no_activation_response()

    async def cancel(self, activation_id: str) -> dict[str, Any]:
        """Cancel an activation and keep a terminal summary."""
        entry = require_entry(self._registry, activation_id)
        entry.local_workflow_state = ActivationLocalState.CANCELLING

        try:
            payload = await self._client.cancel_activation(activation_id)
        except JarvisActivationAPIError as error:
            if error.status == 409:
                return await self.get_status(activation_id)
            raise

        entry.confirmation_token = None
        entry.retry_token = None
        entry = self._registry.update_from_activation_payload(payload)
        return activation_prompt_response(
            entry,
            message="The requested action was cancelled.",
        )

    async def cancel_follow_up(
        self,
        *,
        activation_id: str | None = None,
        conversation_context_id: str | None = None,
        summary_hint: str | None = None,
    ) -> dict[str, Any]:
        """Resolve and cancel a natural follow-up cancellation request."""
        if activation_id:
            return await self.cancel(activation_id)

        active_entries = self._candidate_entries(
            conversation_context_id=conversation_context_id,
        )

        if summary_hint:
            active_entries = _entries_matching_summary(active_entries, summary_hint)

        if len(active_entries) == 1:
            return await self.cancel(active_entries[0].activation_id)

        if len(active_entries) > 1:
            return clarification_response(active_entries)

        return no_activation_response()

    async def _result_or_status(self, entry: ActivationEntry) -> dict[str, Any]:
        if (
            entry.status == "COMPLETED"
            and entry.latest_activation_snapshot.get("result_available") is True
            and not entry.result_fetched
        ):
            entry.local_workflow_state = ActivationLocalState.FETCHING_RESULT
            result = await self._client.get_activation_result(entry.activation_id)
            entry.result_fetched = True
            entry.result_payload = result
            entry.local_workflow_state = ActivationLocalState.DONE
            return {
                "success": True,
                "status": "completed",
                "state": entry.status,
                "summary": entry.user_facing_summary,
                "message": status_message_for(entry),
                "activation_result": result.get("result"),
                "result_fetched": True,
            }

        return activation_prompt_response(entry)

    def _candidate_entries(
        self,
        *,
        conversation_context_id: str | None,
    ) -> list[ActivationEntry]:
        same_context = (
            self._registry.active_entries(
                conversation_context_id=conversation_context_id,
            )
            if conversation_context_id is not None
            else []
        )

        if same_context:
            return same_context

        return self._registry.active_entries()

    async def _summarize_entries(
        self,
        entries: list[ActivationEntry],
    ) -> dict[str, Any]:
        refreshed = []

        for entry in entries:
            refreshed_response = await self.get_status(entry.activation_id)
            refreshed.append(_public_status_item(refreshed_response, entry))

        return {
            "success": True,
            "status": "multiple",
            "message": "There are multiple activation requests being tracked.",
            "activations": refreshed,
        }


def extract_activation_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract and validate a public activation snapshot from an API payload."""
    result = payload.get("result")

    if not isinstance(result, dict):
        raise ValueError("Activation API returned an invalid result.")

    activation = result.get("activation")

    if not isinstance(activation, dict):
        raise ValueError("Activation API returned an invalid activation snapshot.")

    activation_id = activation.get("activation_id")

    if not isinstance(activation_id, str) or not activation_id:
        raise ValueError("Activation API returned an invalid activation id.")

    return dict(activation)


def require_entry(
    registry: ActivationRegistry,
    activation_id: str,
) -> ActivationEntry:
    """Return a tracked entry or fail with a stable local error."""
    entry = registry.get(activation_id)

    if entry is None:
        raise ValueError("Activation is not known to this Home Assistant runtime.")

    return entry


def activation_prompt_response(
    entry: ActivationEntry,
    *,
    message: str | None = None,
) -> dict[str, Any]:
    """Build a structured Claude-facing activation summary."""
    return {
        "success": True,
        "status": _status_label(entry),
        "state": entry.status,
        "local_workflow_state": entry.local_workflow_state.value,
        "capability": entry.capability_name,
        "summary": entry.user_facing_summary,
        "message": message or status_message_for(entry),
        "result_fetched": entry.result_fetched,
    }


def no_activation_response() -> dict[str, Any]:
    """Return a natural no-active-activation response."""
    return {
        "success": True,
        "status": "none",
        "message": "No pending activation is currently being tracked.",
        "activations": [],
    }


def clarification_response(entries: list[ActivationEntry]) -> dict[str, Any]:
    """Return a natural clarification prompt without activation IDs."""
    return {
        "success": True,
        "status": "needs_clarification",
        "message": "There are multiple activation requests. Ask which one the user means.",
        "choices": [
            {
                "summary": entry.user_facing_summary,
                "state": entry.status,
                "status": _status_label(entry),
            }
            for entry in entries
        ],
    }


def status_message_for(entry: ActivationEntry) -> str:
    """Map backend lifecycle state to natural conversational wording."""
    status = entry.status

    if status == "PENDING_CONFIRMATION":
        return "This request is waiting for user confirmation."

    if status == "WAITING_FOR_AGENT":
        return "The PC is still starting."

    if status == "EXECUTING_CAPABILITY":
        return "The PC is ready and the requested task is running."

    if status == "WAITING_RETRY_CONFIRMATION":
        if entry.retry_token is None:
            return (
                "The PC still is not reachable. Another wake attempt cannot "
                "currently be initiated automatically, so restarting the "
                "original request may be necessary."
            )

        return "The PC still is not reachable. Ask whether another wake attempt should be made."

    if status == "COMPLETED":
        return "The requested task completed successfully."

    if status == "FAILED":
        failure_reason = entry.latest_activation_snapshot.get("failure_reason_code")

        if isinstance(failure_reason, str) and failure_reason:
            return f"The requested task failed. Reason code: {failure_reason}."

        return "The requested task failed."

    if status == "CANCELLED":
        return "The requested action was cancelled."

    return "The activation status is available."


def _status_label(entry: ActivationEntry) -> str:
    status = entry.status

    return {
        "PENDING_CONFIRMATION": "waiting_for_confirmation",
        "WAITING_FOR_AGENT": "starting",
        "EXECUTING_CAPABILITY": "executing",
        "WAITING_RETRY_CONFIRMATION": "waiting_for_retry_confirmation",
        "COMPLETED": "completed",
        "FAILED": "failed",
        "CANCELLED": "cancelled",
    }.get(status or "", "unknown")


def _entries_matching_summary(
    entries: list[ActivationEntry],
    summary_hint: str,
) -> list[ActivationEntry]:
    normalized_hint = summary_hint.strip().casefold()

    if not normalized_hint:
        return entries

    return [
        entry
        for entry in entries
        if normalized_hint in entry.user_facing_summary.casefold()
        or normalized_hint in entry.capability_name.casefold()
    ]


def _public_status_item(
    response: dict[str, Any],
    entry: ActivationEntry,
) -> dict[str, Any]:
    return {
        "summary": entry.user_facing_summary,
        "state": response.get("state", entry.status),
        "status": response.get("status", _status_label(entry)),
        "message": response.get("message", status_message_for(entry)),
        "result_fetched": response.get("result_fetched", entry.result_fetched),
    }
