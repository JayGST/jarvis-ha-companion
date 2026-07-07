# JARVIS Home Assistant Companion

## Purpose

This repository contains the Home Assistant companion integration for Project JARVIS.

The companion integration is the Home Assistant LLM adapter for JARVIS.

It registers official Home Assistant LLM tools and forwards tool requests to the JARVIS Add-on backend.

This repository is **not** a Home Assistant Add-on.

The Project-JARVIS Add-on must be installed and running separately because it owns the backend Capability API and all JARVIS business logic.

---

## Current Status

The Companion Integration is implemented as a Home Assistant custom integration with config-entry setup.

It registers a JARVIS LLM API and exposes Project Knowledge tools to Home Assistant Assist / Claude.

The integration communicates with the Project-JARVIS Add-on through the Add-on HTTP Capability API.

It does not execute Project Knowledge logic itself.

---

## Architectural Boundary

All business logic remains in the JARVIS Add-on.

The companion integration must stay thin.

It must not inspect project files, query Home Assistant entities directly for JARVIS logic, or duplicate backend services.

Its responsibility is to translate between:

```text
Home Assistant Assist / Claude
  -> Home Assistant LLM tools
  -> JARVIS Companion Integration
  -> JARVIS Add-on HTTP Capability API
```

---

## Current Project Knowledge Tools

The Companion Integration currently registers these Project Knowledge LLM tools:

* `inspect_project_module` - inspect one specific project item, feature, capability or implementation detail.
* `list_capabilities` - list currently implemented JARVIS capabilities.
* `list_extensions` - list installed optional JARVIS extensions.
* `get_ideas` - list documented ideas from the JARVIS idea collection.
* `get_roadmap_items` - list documented roadmap items.
* `find_decision` - find accepted architecture decisions.

User-facing questions should prefer the current taxonomy:

* Capabilities
* Extensions
* Ideas
* Roadmap
* Decisions

The Companion should not present software modules as the preferred user-facing concept.

---

## Manual Installation

1. Install and start the Project-JARVIS Add-on first.
2. Copy this folder into Home Assistant's configuration directory:

```text
custom_components/jarvis_ha_companion/
```

The resulting Home Assistant path should be:

```text
/config/custom_components/jarvis_ha_companion/
```

3. Restart Home Assistant.
4. Open Home Assistant Settings.
5. Go to Devices & services.
6. Add the JARVIS Home Assistant Companion integration.
7. Enter the JARVIS Add-on base URL.

---

## Base URL Configuration

The `base_url` value points to the running Project-JARVIS Add-on Capability API.

For a local development test this may look like:

```text
http://127.0.0.1:8099
```

Inside Home Assistant, the final URL depends on how the Add-on exposes its HTTP port on the Home Assistant internal network.

Do not include the endpoint path. The integration appends:

```text
/api/v1/capabilities/execute
```

---

## Test Checklist

Before testing the conversation flow:

1. Project-JARVIS Add-on is installed.
2. Project-JARVIS Add-on is running.
3. Capability API is reachable from Home Assistant.
4. `base_url` is configured in the companion integration.
5. Home Assistant Assist uses an LLM conversation agent such as Claude.
6. The JARVIS LLM API is available to the conversation agent.
7. The current Project Knowledge tools are visible to the LLM agent.
8. Ask source-backed Project Knowledge questions, for example:

```text
Welche F?higkeiten hast du?
Welche Erweiterungen hast du?
Welche Ideen sind dokumentiert?
Was steht als n?chstes auf der Roadmap?
Welche Entscheidung gibt es zur JARVIS Identit?t?
```

Expected behavior:

* Home Assistant routes the tool call to the companion integration.
* The companion integration forwards the request to the Add-on Capability API.
* The Add-on returns the structured ProjectKnowledgeService result.
* The companion integration returns the Add-on response without adding business logic.

---

## Current Scope

The current implementation provides:

1. Home Assistant config-entry setup.
2. JARVIS LLM API registration.
3. Project Knowledge LLM tool registration.
4. HTTP forwarding through `JarvisAddonClient`.
5. Structured response passthrough from the Project-JARVIS Add-on.

Deferred work includes advanced error mapping, retry behavior, streaming responses and future tools for memory, finance, Windows and context capabilities.
