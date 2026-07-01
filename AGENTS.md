# AGENTS.md

# JARVIS Home Assistant Companion - AI Development Guide

This repository contains the Home Assistant companion integration for Project JARVIS.

The integration must remain a thin adapter.

---

# Core Rules

* Do not add JARVIS business logic to this repository.
* Do not duplicate logic from the JARVIS Add-on.
* Do not inspect project files from this integration.
* Do not implement project knowledge, memory, finance, Windows or context logic here.
* Register Home Assistant LLM tools only when the architecture has been approved.
* Forward capability requests to the JARVIS Add-on backend.
* Keep the integration small and Home Assistant-specific.

---

# Responsibility Boundary

## Companion Integration

Owns:

* Home Assistant custom integration structure.
* Home Assistant LLM API registration.
* Home Assistant LLM tool definitions.
* Translation between Home Assistant tool calls and Add-on capability requests.

## JARVIS Add-on

Owns:

* Business logic.
* ProjectKnowledgeService.
* HomeAssistantEntityQueryService.
* Future Memory, Finance, Windows and Context services.
* Capability execution.

---

# Development Rule

If a feature requires business logic, it belongs in the JARVIS Add-on, not in this repository.
