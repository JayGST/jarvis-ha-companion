# Architecture

## Purpose

This document describes the architecture of the JARVIS Home Assistant Companion integration.

The Companion Integration is the Home Assistant LLM adapter for Project JARVIS.

It exposes JARVIS capabilities to Home Assistant Assist / Claude while keeping all business logic inside the Project-JARVIS Add-on.

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

Contains no JARVIS business logic.

## JarvisAddonClient

Owns the minimal HTTP client boundary to the Project-JARVIS Add-on Capability API.

It sends the Capability API request envelope and returns the structured Add-on response.

It does not interpret capability results.

## HTTP Capability API

Provides the request/response boundary between the Companion Integration and the JARVIS Add-on.

The current transport is HTTP.

## JARVIS Add-on

Owns all JARVIS business logic and capability execution.

Project Knowledge capabilities are backed by ProjectKnowledgeService inside the Add-on.

---

# Current LLM Tools

The Companion Integration currently registers multiple Project Knowledge LLM tools:

* `inspect_project_module`
* `list_capabilities`
* `list_extensions`
* `get_ideas`
* `get_roadmap_items`
* `find_decision`

Each tool forwards directly to the matching Add-on capability.

No tool contains Project Knowledge business logic.

---

# Architecture Principle

The Companion Integration must stay replaceable.

All durable JARVIS behavior belongs in the Add-on backend.

The Companion Integration is an adapter, not a second JARVIS brain.
