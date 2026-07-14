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
* `get_runtime_status`

Each tool forwards directly to the matching Add-on capability.

`get_runtime_status` is a read-only runtime reachability tool. It has no parameters and forwards to the Project-JARVIS runtime health capability through `JarvisAddonClient`.

No tool contains Project Knowledge, Windows Agent, routing, or orchestration business logic. Project-JARVIS owns routing and capability execution.

---

# Architecture Principle

The Companion Integration must stay replaceable.

All durable JARVIS behavior belongs in the Add-on backend.

The Companion Integration is an adapter, not a second JARVIS brain.
