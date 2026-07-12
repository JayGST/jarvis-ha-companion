# JARVIS Home Assistant Companion

## Purpose

This repository contains the Home Assistant companion integration for Project JARVIS.

The companion integration is the Home Assistant LLM adapter for JARVIS.

It registers official Home Assistant LLM tools and forwards tool requests to the JARVIS Add-on backend.

This repository is **not** a Home Assistant Add-on.

The Project-JARVIS Add-on must be installed and running separately because it owns the backend Capability API and all JARVIS business logic.

Project-JARVIS also owns the canonical JARVIS identity prompt. The Companion Integration fetches that runtime identity through the `get_identity_prompt` capability and injects it into the Home Assistant LLM API prompt.

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

The Companion may cache and inject the runtime identity prompt returned by Project-JARVIS, but it must not maintain a second full copy of the JARVIS identity or personality rules.

The Companion owns only technical Home Assistant tool instructions and capability routing guidance.

---

## Runtime Identity

Runtime Identity Integration is complete.

During integration setup, the Companion calls the Add-on Capability API:

```text
capability: get_identity_prompt
```

The returned prompt is cached in memory and used when registering the Home Assistant LLM API.

The cached runtime prompt is injected into the Home Assistant LLM API prompt before Companion-specific tool instructions.

Identity refresh currently happens on Home Assistant integration reload or restart. There is no background polling.

If Project-JARVIS or `get_identity_prompt` is unavailable, setup still completes. The Companion logs a warning and uses a short neutral fallback that contains only essential tool instructions.

User preferences and dynamic speech settings are not implemented yet.

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

## First Test Checklist

Before testing the conversation flow:

1. Project-JARVIS Add-on is installed.
2. Project-JARVIS Add-on is running.
3. Capability API is reachable from Home Assistant.
4. `base_url` is configured in the companion integration.
5. Home Assistant Assist uses an LLM conversation agent such as Claude.
6. The `inspect_project_module` tool is visible to the LLM agent.
7. Ask a project knowledge question, for example:

```text
Is the stock module installed?
```

Expected behavior:

* Home Assistant routes the tool call to the companion integration.
* The companion integration forwards the request to the Add-on Capability API.
* The Add-on returns the structured ProjectKnowledgeService result.
* The companion integration does not interpret the result itself.

---

## Genesis Scope

The Genesis implementation focuses on:

1. Registering a custom Home Assistant LLM API.
2. Adding the first tool, `inspect_project_module`.
3. Forwarding the tool request to the JARVIS Add-on HTTP Capability API.
4. Performing the first end-to-end conversation test.
