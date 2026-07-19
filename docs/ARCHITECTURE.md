# Architecture

## Purpose

This document describes the architecture of the JARVIS Home Assistant Companion integration.

The Companion Integration is the Home Assistant LLM adapter for Project JARVIS.

It exposes JARVIS capabilities to Home Assistant Assist / Claude while keeping all business logic inside the Project-JARVIS Add-on.

Project-JARVIS owns the canonical JARVIS identity. The Companion Integration consumes that identity at runtime and does not keep a duplicate identity summary.

---

# System Flow

```text
Home Assistant Assist / Claude
  |
  v
Home Assistant LLM tool
  |
  v
JARVIS Companion Integration
  |
  v
JarvisAddonClient
  |
  v
Project-JARVIS Add-on Capability API
  |
  v
Project-JARVIS Add-on services
```

---

# Responsibilities

## Home Assistant Assist / Claude

Owns conversation, reasoning and Home Assistant LLM tool execution.

## JARVIS Companion Integration

Registers official Home Assistant LLM tools.

Forwards tool calls to the JARVIS Add-on through `JarvisAddonClient`.

Returns structured Add-on responses without interpreting Project Knowledge results.

Fetches and caches the runtime identity prompt during integration setup so it can be injected into the Home Assistant LLM API prompt.

Contains no JARVIS business logic.

## JarvisAddonClient

Owns the minimal HTTP client boundary to the Project-JARVIS Add-on Capability API.

It sends the Capability API request envelope and returns the structured Add-on response.

It does not interpret capability results.

For `get_identity_prompt`, it validates the response shape and returns the runtime prompt metadata without rewriting the identity.

## HTTP Capability API

Provides the request/response boundary between the Companion Integration and the JARVIS Add-on.

The current transport is HTTP.

## JARVIS Add-on

Owns all JARVIS business logic and capability execution.

Project Knowledge capabilities are backed by ProjectKnowledgeService inside the Add-on.

The `get_identity_prompt` capability returns the canonical identity prompt from Project-JARVIS.

---

# Prompt Composition

Runtime Identity Integration is complete.

The Home Assistant LLM API prompt is assembled in a fixed order:

1. Runtime JARVIS identity returned by Project-JARVIS.
2. Companion/API tool instructions.
3. Capability-specific guidance.

The Companion owns only the technical tool instructions and routing guidance. It does not own JARVIS personality rules, user preferences, or dynamic speech settings.

If the identity capability is unavailable, the Companion logs a warning and uses a short neutral fallback. It does not restore a copied static identity summary.

Identity refresh currently occurs on Home Assistant integration reload or restart. There is no background polling.

The Companion caches only the runtime identity text returned during setup. It does not transform, summarize, or reinterpret the identity supplied by Project-JARVIS.

---

# Current LLM Tools

The Companion Integration currently registers multiple LLM tools, including Project Knowledge tools and runtime status tools:

* `inspect_project_module`
* `list_capabilities`
* `list_extensions`
* `get_ideas`
* `get_roadmap_items`
* `find_decision`
* `search_project`
* `repository_file_exists`
* `list_repository_directory`
* `read_repository_file`
* `get_runtime_status`
* `get_runtime_info`
* `get_runtime_capabilities`
* `get_system_metrics`
* `launch_application`
* `get_activation_status`
* `confirm_activation`
* `retry_activation`
* `cancel_activation`

Each tool forwards directly to the matching Add-on capability.

`search_project` is a read-only Project Knowledge search adapter. It accepts a required query and optional limit, then forwards those parameters to Project-JARVIS without implementing search logic locally.

The repository filesystem tools are dedicated read-only adapters with fixed Project-JARVIS capability mappings:

* `repository_file_exists` -> `filesystem.file_exists`
* `list_repository_directory` -> `filesystem.list_directory`
* `read_repository_file` -> `filesystem.read_file`

They accept only `repository_id` and `relative_path`. `repository_id` refers to a repository explicitly approved in Project-JARVIS configuration, and `relative_path` is relative to that approved repository. The Companion does not provide arbitrary filesystem access, absolute path access, or write operations. Project-JARVIS owns authorization and routing. The Windows Agent owns final repository-root and path enforcement.

The runtime tools are read-only and accept no parameters:

* `get_runtime_status` forwards current reachability and health checks to Project-JARVIS.
* `get_runtime_info` forwards runtime information requests to Project-JARVIS.
* `get_runtime_capabilities` forwards Windows Agent capability listing requests to Project-JARVIS.
* `get_system_metrics` forwards live system-metrics snapshot requests to Project-JARVIS.

Capability discovery is informational. A Windows Agent capability inventory describes operations implemented and advertised by the Agent; it is not the same as Claude tool availability. Companion exposure remains explicit and allowlisted through the tools registered in this integration.

`get_system_metrics` is a dedicated read-only adapter for the fixed `system.metrics` capability. Project-JARVIS owns routing, the Windows Agent owns metric collection, and the Companion performs no local collection or interpretation. Optional metrics may be unavailable, and responses should include only the metrics relevant to the user's question unless raw metrics are explicitly requested.

`launch_application` is a dedicated adapter for the fixed `application.launch` capability. It accepts only approved application ID enum values and forwards that value to Project-JARVIS. The Companion does not accept raw paths, shortcut paths, arguments, working directories, environment variables, discovery settings, local overrides, provider selection or direct Windows Agent communication.

Activation lifecycle tools are dedicated adapters for Project-JARVIS Activation API resources. The Companion can check activation status, confirm one pending activation with the stored one-time confirmation token, retry one retry-waiting activation with the stored retry token when available, or cancel one activation. Activation entries are retained in memory only and are keyed by activation ID, but user-facing follow-up conversations do not require the user to know activation IDs.

Conversation continuation is request/response. Home Assistant does not let the Companion resume a finished Claude response autonomously. Instead, natural follow-up requests such as "Is my PC ready?", "Is everything finished?", "How far are you?", "Continue", or "Cancel it" cause Claude to call the activation tools again. The Companion resolves the relevant activation from the current conversation context, stored user-facing summaries and active activation registry. A single active activation is selected automatically. Multiple matching activations produce a clarification response that lists summaries only. If no activation is pending, the Companion returns a natural no-active-request response.

Status checks refresh the stored activation snapshot through `GET /api/v1/activations/{activation_id}`. When a refreshed status is `COMPLETED` and `result_available` is true, the Companion calls `GET /api/v1/activations/{activation_id}/result` exactly once and caches the returned result in memory. Later status checks reuse the cached result state instead of fetching the retained result again.

Tokens are removed immediately after accepted or idempotent confirmation and retry calls, and terminal activation summaries are cleaned up lazily. The Companion does not persist activation state, expose token fields to Claude, create backend activation jobs, wake devices directly, use notifications, use WebSockets, or ask Project-JARVIS to execute client-resubmitted capability arguments.

No tool contains Project Knowledge, Windows Agent, routing, or orchestration business logic. Project-JARVIS owns routing and capability execution.

---

# Architecture Principle

The Companion Integration must stay replaceable.

All durable JARVIS behavior belongs in the Add-on backend.

The Companion Integration is an adapter, not a second JARVIS brain.
