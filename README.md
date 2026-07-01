# JARVIS Home Assistant Companion

## Purpose

This repository contains the Home Assistant companion integration for Project JARVIS.

The companion integration is the Home Assistant LLM adapter for JARVIS.

It registers official Home Assistant LLM tools and forwards tool requests to the JARVIS Add-on backend.

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

## Genesis Scope

The Genesis implementation will focus on:

1. Registering a custom Home Assistant LLM API.
2. Adding the first tool, `inspect_project_module`.
3. Forwarding the tool request to the JARVIS Add-on HTTP Capability API.
4. Performing the first end-to-end conversation test.

No real tools or HTTP calls are implemented in this initial skeleton.
