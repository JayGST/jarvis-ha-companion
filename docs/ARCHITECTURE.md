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

No tool contains Project Knowledge, Windows Agent, routing, or orchestration business logic. Project-JARVIS owns routing and capability execution.

---

# Architecture Principle

The Companion Integration must stay replaceable.

All durable JARVIS behavior belongs in the Add-on backend.

The Companion Integration is an adapter, not a second JARVIS brain.
