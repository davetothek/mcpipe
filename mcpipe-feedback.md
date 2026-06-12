# mcpipe Feedback Log

Use this file to capture actionable findings for the maintainer.

## Entry format
- Date: YYYY-MM-DD
- Type: bug | suggestion
- Area: server | fs | git | docker | compose | cache | docs | other
- Summary: one-line description
- Repro/Context: short steps or command/tool call context
- Expected: what should happen
- Actual: what happened
- Impact: low | medium | high
- Proposed fix: optional implementation idea
- Status: open | fixed | wontfix

## Entries
- Date: 2026-06-10
- Type: suggestion
- Area: docs
- Summary: Moved mcpipe workflow guidance from repo-level files to HOME-level Copilot settings.
- Repro/Context: Shared repository should avoid personal Copilot policy files.
- Expected: Policy follows user across workspaces without modifying shared repo.
- Actual: HOME settings updated and HOME log file created.
- Impact: medium
- Proposed fix: n/a
- Status: fixed

- Date: 2026-06-11
- Type: bug
- Area: other
- Summary: run_in_terminal async idle result can be followed by invalid get_terminal_output ID lookup.
- Repro/Context: After run_in_terminal(mode=async) returned terminal id 2d45fa6b-9592-400f-978e-1fae26b8e24d with idle output, immediate get_terminal_output on same id returned "No active terminal execution found" even though run output was still being reported via notification flow.
- Expected: Either get_terminal_output should accept the provided id until completion, or async response should clearly mark the id as already finalized/cleaned.
- Actual: Inconsistent state between returned id and retrievable execution.
- Impact: medium
- Proposed fix: Keep terminal execution queryable until completion notification, or return a stable artifact handle when execution is auto-finalized.
- Status: open

- Date: 2026-06-12
- Type: suggestion
- Area: docs
- Summary: authoring_help(topic='transform') should include copy-paste runnable examples and explicit transform contract details.
- Repro/Context: During delta transform authoring, authoring_help returned high-level guidance and a cached handle preview, but implementation still required source-level inspection to confirm signature and return shape.
- Expected: Help output should be sufficient to implement a transform without reading mcpipe internals.
- Actual: Required extra exploration to infer exact function signature and output contract.
- Impact: medium
- Proposed fix: Extend authoring_help with a compact “minimum viable transform” section (decorator signature, input/output schema, error behavior), include one file-oriented and one handler-output example, and include direct instructions for viewing full cached help content.
- Status: fixed

- Date: 2026-06-12
- Type: suggestion
- Area: other
- Summary: Tool references can appear in chat attachments but remain non-callable in active tool registry.
- Repro/Context: User attached drawio tool references (mcp_drawio-mcp_open_drawio_mermaid/csv/xml) after reload; agent still could not invoke these names as executable tools in runtime despite MCP being available for other servers.
- Expected: Attached tool references should be callable immediately, or client should display explicit "metadata only, not callable" state.
- Actual: Ambiguous availability caused repeated failed attempts and user confusion.
- Impact: medium
- Proposed fix: Add a runtime availability check badge for each attached tool reference and expose a deterministic probe endpoint.
- Status: open

- Date: 2026-06-12
- Type: suggestion
- Area: fs
- Summary: Add native surrounding-context arguments to search tools instead of requiring a separate transform.
- Repro/Context: `mcp_mcpipe_fs_grep` currently returns match lines only (`path:line:content`). For investigation workflows, users then need extra reads or a custom transform to see nearby lines.
- Expected: Search call should optionally return surrounding lines in one request.
- Actual: No native `before/after/context` options in search tool schema.
- Impact: medium
- Proposed fix: Add `before` and `after` integer args (or `context` shorthand) to `fs_grep`; keep output as merged context blocks per file with stable `path:line` prefixes. Optionally keep `surround` transform for generic post-processing, but make search-context first-class.
- Status: fixed
