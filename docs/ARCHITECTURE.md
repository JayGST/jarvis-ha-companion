# Architecture

## Purpose

This document describes the Genesis architecture of the JARVIS Home Assistant Companion integration.

---

# System Flow

```text
Home Assistant Assist / Claude
  |
  v
JARVIS Companion Integration
  |
  v
HTTP Capability API
  |
  v
JARVIS Add-on
```

---

# Responsibilities

## Home Assistant Assist / Claude

Owns conversation, reasoning and Home Assistant LLM tool execution.

## JARVIS Companion Integration

Registers official Home Assistant LLM tools.

Forwards tool calls to the JARVIS Add-on.

Contains no JARVIS business logic.

## HTTP Capability API

Provides the request/response boundary between the Companion Integration and the JARVIS Add-on.

The Genesis transport is HTTP.

## JARVIS Add-on

Owns all JARVIS business logic and capability execution.

The first planned capability is backed by ProjectKnowledgeService.

---

# Genesis Principle

The Companion Integration must stay replaceable.

All durable JARVIS behavior belongs in the Add-on backend.
