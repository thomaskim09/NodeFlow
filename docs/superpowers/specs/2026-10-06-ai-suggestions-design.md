# Phase 1 AI-Assisted Coding Suggestions

## Intent

Add an optional, researcher-controlled workflow that proposes coding nodes for
the currently selected document text. The AI may suggest names and reasons, but
it never writes coding data or creates nodes. SQLite changes occur only after an
explicit researcher action.

Success means that a researcher can select text, opt in to an external request,
review temporary suggestions matched to existing nodes, accept an existing
node, edit a suggestion name, or reject it. AI suggestions never create nodes.
Existing coding, undo/redo, refresh, highlighting, statistics, localization,
and database behavior remain intact.

## Constraints and non-goals

- Send only selected text and the minimum node hierarchy needed for matching.
- Do not send the complete project, transcript, participant ID, or project ID.
- Require explicit privacy confirmation before each external request.
- Read the API key from `NODEFLOW_AI_API_KEY` or local settings, with the
  environment variable taking precedence.
- When saved through Settings, protect the local settings file from group and
  other-user access; never include the key in project exports.
- Every AI suggestion must reference one supplied existing node ID; null,
  invented, or new-node suggestions are rejected.
- Never log API keys, authorization headers, selected text, or full prompts.
- Keep suggestions in memory; do not add suggestion-history tables.
- Do not add authentication, a backend, embeddings, RAG, agents, batch coding,
  dashboards, synchronization, or executable workflow nodes.
- Use the Python standard library for HTTP so Phase 1 adds no dependency.

## Existing architecture to reuse

- `WorkspaceView` owns workspace actions, selection state, `WorkspaceHistory`,
  and the existing `code_selection()` command.
- `ContentView` exposes the active `QTextEdit`, document ID, participant ID,
  selection signal, and coded-segment highlight cache.
- `TaskThread` runs blocking work without blocking the Qt event loop.
- The `database` facade routes node and coded-segment writes to repositories.
- `WorkspaceSnapshotRepository` restores nodes and coded segments for undo/redo.
- `WorkspaceView.refresh_all_views()`, `on_segments_changed()`, and
  `refresh_coding_stats()` provide the established refresh paths.
- English and Chinese UI text is stored in `locales/en.yml` and `locales/zh.yml`.

## Selected approach

Use an isolated provider interface implemented with `urllib.request`. Gemini is
the default native provider: it calls `generateContent`, authenticates with
`X-goog-api-key`, and requests JSON with `responseMimeType: application/json`.
The existing OpenAI-compatible provider remains available by setting
`NODEFLOW_AI_PROVIDER=openai_compatible`. The workspace Settings dialog can
save the provider, API key, model, and optional endpoint locally. Environment
variables override saved values; `NODEFLOW_GEMINI_API_URL` remains available
for overriding Gemini's native endpoint.
The default Gemini model is `gemini-flash-lite-latest`; `NODEFLOW_AI_MODEL`
can select another model when needed.

`AISuggestionService` accepts selected text and a minimal list of existing node
records, constructs the strict-JSON request, calls the provider, extracts the
JSON response, and validates it into temporary `AISuggestion` objects. The
service has no repository or database imports. Its transport is injectable for
tests.

## Service contract

The response must contain:

```json
{
  "suggestions": [
    {
      "name": "Suggested code",
      "reason": "Short explanation",
      "existing_node_id": 7
    }
  ]
}
```

Validation rules:

- `suggestions` exists and is a list.
- Every `name` is a non-empty string after trimming.
- Every `reason` is a string.
- `existing_node_id` is an integer in the supplied node ID set.
- Malformed JSON, missing fields, invalid IDs, and provider failures raise a
  user-safe service error without touching the database.
- The request asks for approximately three to five suggestions but does not
  require an exact count.

## Researcher workflow

1. The researcher selects text in the active document.
2. The `WorkspaceView` toolbar action, `AI Suggestions`, sits beside Save and
   becomes enabled only while a valid selection exists and the workspace is
   not in segment-edit mode.
3. The action captures document ID, participant ID, start/end offsets, selected
   text, and the minimal existing node hierarchy (`id`, `name`, `parent_id`).
4. A privacy confirmation explains that the selected research text will be sent
   to an external AI provider. Cancel leaves the project unchanged.
5. `TaskThread` calls the service. The action is disabled and a loading state is
   shown until the worker succeeds or fails.
6. On success, `AISuggestionDialog` displays each temporary suggestion with its
   name, reason, and whether it matches an existing NodeFlow node.
7. `Edit` changes the suggested node name in memory. `Reject` removes the card
   without persistence.
8. `Accept` validates the captured selection and uses the existing coded-segment
   command path for the matched existing node.

## Selection safety and persistence

Before any accept action, verify that:

- the active document ID is unchanged;
- the captured offsets satisfy `0 <= start < end <= current_text_length`;
- the current text at the captured range exactly matches the captured text.

If validation fails, show a clear stale-selection message and make no database
change. Dirty document text is saved only through the existing coding path after
validation, preserving current behavior.

Existing-node acceptance reuses the current `WorkspaceView.code_selection()`
command, including segment snapshots, undo/redo, highlight refresh, segment
refresh, and statistics refresh.

No suggestion action creates a node. Rejected suggestions and cancelled dialogs
perform no writes.

## Privacy and error handling

- Missing API-key configuration produces a friendly message and skips the
  request.
- Network, HTTP, timeout, and malformed-response failures produce generic,
  actionable messages without exposing provider response bodies or participant
  text.
- No AI failure changes SQLite or the current selection.
- The default provider configuration is replaceable through the Settings dialog
  or environment settings.

## Files

Create:

- `services/ai_suggestion_service.py`
- `services/settings_service.py`
- `ui/workspace/ai_suggestion_dialog.py`
- `tests/test_ai_suggestion_service.py`
- `tests/test_ai_suggestion_workflow.py`

Modify:

- `ui/workspace/workspace_view.py`
- `locales/en.yml`
- `locales/zh.yml`
- `README.md`
- `FEATURE_INVENTORY.md`

No database schema or repository API changes are planned.

## Verification

Automated coverage will include valid parsing, malformed JSON, missing
suggestions, empty names, invalid node IDs, missing keys, provider failures,
database stability after rejection, existing-node acceptance, undo/redo, and
the service's lack of persistence behavior. Network calls will be mocked; tests
will never require a real key or external service.

Run the targeted tests, the full test suite, and Ruff checks after
implementation. Manual verification will cover selection enablement, privacy
confirmation, loading/error states, stale selections, edit/reject actions, and
existing-node-only acceptance.
