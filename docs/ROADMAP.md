# Roadmap

## Genesis

Status:

Completed

Goal:

Create the minimal Home Assistant companion integration needed to expose JARVIS capabilities to Home Assistant Assist and Claude.

Completed:

1. Register custom LLM API.
2. Add config-entry setup.
3. Add `inspect_project_module` tool.
4. Connect to Add-on HTTP Capability API through `JarvisAddonClient`.
5. Complete end-to-end testing with the Project-JARVIS Add-on.
6. Add the current Project Knowledge tool set.
7. Complete Runtime Identity Integration.
8. Add dedicated read-only runtime LLM tools.

Runtime Identity Integration:

* Companion no longer owns the JARVIS identity.
* Project-JARVIS provides the canonical identity through `get_identity_prompt`.
* Companion loads and caches identity during setup.
* Companion injects the runtime prompt into the Home Assistant LLM API prompt.
* Companion keeps only technical tool instructions and capability routing guidance.
* Companion uses a neutral fallback if Project-JARVIS identity loading is unavailable.

Current implemented tools:

* `inspect_project_module`
* `list_capabilities`
* `list_extensions`
* `get_ideas`
* `get_roadmap_items`
* `find_decision`
* `get_runtime_status`
* `get_runtime_info`
* `get_runtime_capabilities`

Runtime tools:

* `get_runtime_status` lets Home Assistant / Claude ask whether the Windows Agent, main PC, or desktop runtime is currently reachable.
* `get_runtime_info` lets Home Assistant / Claude ask for Windows Agent runtime information such as hostname, operating system, platform, architecture, and Python runtime information.
* `get_runtime_capabilities` lets Home Assistant / Claude ask which Windows Agent capabilities or functions are available.
* The Companion maps each runtime tool to a fixed Project-JARVIS capability and does not contact the Windows Agent directly.
* Project-JARVIS remains the orchestrator and owner of routing.

---

## Current Focus

Keep the Companion Integration thin and aligned with the Project-JARVIS Capability API.

Tool descriptions and prompt guidance should follow the current Project JARVIS taxonomy:

* Capabilities
* Extensions
* Ideas
* Roadmap
* Decisions

The Companion should continue to consume the canonical identity from Project-JARVIS through `get_identity_prompt`. It should own only Home Assistant-specific tool instructions and capability routing guidance.

Identity refresh currently occurs on Home Assistant integration reload or restart.

---

## Deferred

* Advanced error mapping.
* Retry behavior.
* Streaming responses.
* Additional future tools for memory, finance, Windows and context capabilities.
* Automatic Add-on discovery or connection validation during setup.
* User Preferences.
* Dynamic identity updates.
* Background refresh.
* Speech preferences.
