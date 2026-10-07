# NodeFlow Feature Inventory

This document summarizes what NodeFlow can do based on the current repository source and project documentation.

## Overview

NodeFlow is a desktop qualitative analysis application built with Python and PySide6. It helps researchers manage projects, import text-based research material, create hierarchical codes, apply those codes to text segments, review coded evidence, visualize patterns, and export analysis outputs.

## Project Workflow

- Start from a project selection screen.
- Create new projects.
- Open existing projects.
- Rename projects.
- Delete projects.
- Work inside project-specific workspaces so each project has its own participants, documents, nodes, coded segments, dashboard, and exports.
- Return from a workspace back to the project list.
- Store data in a local SQLite database.
- Keep local user data, logs, imports, exports, settings, and database backups in app data paths.

## Participant Management

- Add participants to a project.
- Rename participants.
- Delete participants.
- View participants in the workspace sidebar.
- Scope participant statistics to the current document or the entire project.
- Show participant-level coded segment counts.
- Show participant coded-word percentages when total word counts are available.
- Select a participant to filter coded segments.
- Clear participant filtering.
- Automatically highlight the participant associated with the currently selected document or coded segment.
- Use keyboard shortcuts for participant list actions:
  - `F2` to rename.
  - `Delete` to delete.

## Document Import

- Import `.txt` files.
- Import `.docx` Word documents.
- Import `.xlsx` Excel workbooks.
- Import multiple files through the file picker.
- Drag and drop supported files into the document view.
- Show a drag-and-drop overlay for supported file types.
- Read Word document paragraphs into editable text.
- Read plain text using UTF-8.
- Copy imported source files into the app data imports folder.
- Store import metadata, including:
  - Source filename.
  - Copied source path.
  - Source SHA-256 hash.
  - Source kind.
  - Source row for Excel imports.
  - Import timestamp.
- Detect duplicate `.txt` or `.docx` documents by project, title, and content, and ask whether to add another copy.
- Prompt for participant assignment when importing text or Word documents.
- If no participant exists, prompt to create the first participant before importing.
- Automatically assign to the only participant when exactly one participant exists.

## Excel Import

- Read headers from the active worksheet in an `.xlsx` file.
- Let the user map Excel columns for:
  - Document title.
  - Main content.
  - Participant name.
- Allow participant assignment to be deferred with `<Assign Later>`.
- Import each valid data row as a document.
- Skip rows with empty title or content.
- Rename duplicate Excel document titles with `copy N` suffixes.
- Create participants automatically from mapped participant-name cells when they do not already exist.
- Run Excel imports in a background task.
- Show import completion summaries.
- Show detailed import errors when some rows fail.
- Make successful Excel imports undoable.

## Document Viewing And Editing

- View imported documents in a document selector.
- Display document titles with participant names.
- Distinguish duplicate title/participant combinations with numbered suffixes.
- Edit document text directly in the workspace.
- Save document text changes.
- Autosave document edits, with configurable delay.
- Enable or disable autosave in settings.
- Prompt before switching documents when there are unsaved changes.
- Delete the current document and its coded segments.
- Track document word count.
- Track coded segment count for the current document.
- Keep coded segment highlights visible in the editor.
- Recalculate coded segment ranges when text is edited.
- Warn before saving edits that would delete coded segments whose selected text was removed.
- Navigate from a coded segment list item to its exact text range in the document.
- Highlight/select text ranges for viewing or segment editing.

## Find And Replace

- Open a find bar from the document editor.
- Pre-fill find text from the current selection.
- Find next match.
- Find previous match.
- Wrap search from the end/start of the document.
- Show match counts.
- Highlight all find matches.
- Configure find-match highlight color in settings.
- Replace the current match after confirmation.
- Replace all matches after confirmation.
- Rebase coded segment ranges during replace-all operations.
- Record replace-all operations in workspace history when applied.

## Coding Text

- Select text in the document editor.
- Click a node in the node tree to code the selected text.
- Optionally request temporary AI suggestions from the editor toolbar after explicit privacy confirmation.
- Enable the AI Suggestions button only when non-empty text is selected.
- Allow AI to suggest existing codes or propose new root codes for researcher review.
- Require explicit Create & Code or Use Existing & Code approval; AI cannot create nodes or autonomously modify coding data.
- Store coded segment start/end positions, text preview, node, document, and participant.
- Highlight coded text using the assigned node color.
- Use readable foreground color based on highlight brightness.
- Auto-save dirty document text before coding a selection.
- Click inside highlighted text to synchronize:
  - The coded segment list.
  - The node tree.
  - The participant list.

## Coded Segment Management

- View coded segments for the current document.
- View coded segments for the entire project.
- Show coded segment columns for:
  - Node color.
  - Coded text preview.
  - Node.
  - Participant.
  - Document, when scoped to entire project.
- Search coded segments.
- Search across all columns.
- Search specifically by coded text, node, participant, or document.
- Filter coded segments by selected node family.
- Filter coded segments by a single node.
- Filter coded segments by selected participant.
- Activate a segment to navigate to its source text.
- Edit a coded segment by selecting a new range in the document.
- Delete coded segments.
- Use `Delete` to remove a selected coded segment.
- Undo segment edits and deletions.

## Hierarchical Node Coding

- Create root nodes.
- Create child nodes.
- Rename nodes.
- Delete nodes and all descendants.
- Delete all codings associated with deleted nodes.
- Change node colors.
- Use a preset color sequence for new nodes.
- Pick custom node colors.
- Organize nodes into a multi-level hierarchy.
- Drag and drop nodes to reorder them.
- Drag and drop nodes to reparent them.
- Automatically update node positions and parent relationships after drag-and-drop.
- Display automatic hierarchical numbering, such as `1.`, `1.1.`, and `1.1.1.`.
- Expand the full node tree.
- Select nodes to filter coded segments by node family.
- Clear node filters.
- Filter by a single node from the node action menu.
- Highlight a node without triggering filtering when navigating from text.
- Use keyboard shortcuts for node tree actions:
  - `F2` to rename.
  - `Delete` to delete.
- Scope node statistics to the current document or the whole project.
- Show aggregate node-family statistics, including:
  - Coded word percentage.
  - Coded segment count.

## Workspace History And Undo/Redo

- Global undo and redo actions in the workspace toolbar.
- Document editor undo and redo buttons.
- Standard keyboard shortcuts for undo and redo.
- Configurable undo history depth.
- Named undo/redo tooltips.
- Undo/redo support for many workspace operations, including:
  - Adding participants.
  - Renaming participants.
  - Deleting participants.
  - Importing documents.
  - Importing Excel documents.
  - Deleting documents.
  - Saving document text.
  - Replace-all operations.
  - Adding root nodes.
  - Adding child nodes.
  - Renaming nodes.
  - Deleting nodes.
  - Moving/reparenting nodes.
  - Changing node colors.
  - Coding selected text.
  - Editing coded segments.
  - Deleting coded segments.

## Dashboard

- Open a dashboard for the current project.
- Start the dashboard scoped to the current document when available.
- Filter dashboard data by:
  - Entire project or selected document.
  - All participants or selected participant.
  - All nodes or selected node family.
- Load dashboard data in a background task.
- Cache dashboard query results.
- Display key metrics:
  - Scope word count.
  - Coded segment count.
  - Coded word count.
  - Coded word percentage.
- Show participant breakdown:
  - Coded words.
  - Percent of total.
  - Segment count.
- Show code breakdown:
  - Hierarchical node tree.
  - Coded words.
  - Percent of total.
  - Segment count.
- Show dashboard tabs for:
  - Breakdown.
  - Charts.
  - Cross-tabulation.
  - Code co-occurrence.
  - Word cloud.
- Switch dashboard theme between light and dark.

## Dashboard Charts And Visualizations

- Bar chart of code distribution.
- Pie chart of code distribution.
- Pie chart groups smaller items into an `Other` slice.
- Use node colors in charts.
- Cross-tabulation table for overlapping coded segments.
- Co-occurrence matrix for codes applied to the same text range.
- Word cloud for coded segment/node activity.
- Apply light/dark styling to charts and tables.

## Dashboard Export

- Export chart or visual tab as a PNG image.
- Export the dashboard code breakdown table as CSV.
- Export co-occurrence matrix as CSV.
- Export co-occurrence network as GEXF for network analysis tools.
- Export cross-tabulation data as CSV.

## Project Export

- Export coded project data to JSON.
- Export coded project report to Word `.docx`.
- Export coded project data to Excel `.xlsx`.
- Export all coded data or selected node-family data.
- Show save dialogs with export-specific file filters.
- Show success dialogs with an option to open exported files.
- Show permission and unexpected-error dialogs for export failures.

## JSON Export

- Export hierarchical node data.
- Include node IDs and node names.
- Include coded segments under each node.
- Include participant name, coded text, and document title for each segment.
- Preserve child node structure recursively.

## Word Export

- Export a full qualitative analysis report.
- Use nodes as hierarchical headings.
- Include coded segments as bullet points under nodes.
- Prefix coded quotes with participant names.
- Export a selected node family and all descendants to Word.
- Export the current document as an annotated Word document.
- In annotated document exports:
  - Preserve the document text.
  - Highlight coded ranges using node colors.
  - Add node labels next to highlighted segments.
  - Use contrasting text color for highlighted runs.

## Excel Export

- Export all project coded segments to a single worksheet.
- Export all project coded segments to multiple worksheets, one per node.
- Export selected node families to a single worksheet.
- Export selected node families to multiple worksheets.
- Export a classification workbook.
- Filter Excel exports by participant.
- Use hierarchical node ordering in Excel output.
- Include participant, coded segment, and document columns.
- Include node names where relevant.
- Set useful worksheet column widths.
- Bold header rows.

## Classification Workbook Export

- Export quotes and respondent/code counts in one workbook.
- Quotes sheet includes:
  - Findings.
  - Node.
  - Sub-node.
  - Respondent.
  - Original quote.
  - Document.
- Respondent matrix sheet includes:
  - Respondent rows.
  - Node-path columns.
  - Counts of coded segments per respondent and code.
- Support whole-project classification exports.
- Support selected node-family classification exports.
- Support participant-filtered classification exports.

## Additional Export Utility

- Code includes an overall participants Excel export utility that creates an `Overall` worksheet with node-level columns and participant quote columns.
- This utility is present in the export manager, though it is not wired into the main workspace export menu in the current UI.

## Settings

- Change application theme between Light and Dark.
- Change language between English and Chinese.
- Configure undo history depth.
- Enable or disable autosave.
- Configure autosave delay in milliseconds.
- Configure find-match highlight color.
- Configure the AI provider, masked API key, model, and optional endpoint.
- Save AI settings locally for reuse on the next startup; environment values override them.
- Apply settings at runtime to the workspace, dashboard, participant list, node tree, document view, and coded segments view.

## Localization

- Store translations in YAML files in `locales/`.
- Use hierarchical translation keys.
- Current language options exposed in the UI:
  - English.
  - Chinese.
- Update many visible UI labels dynamically when language changes.

## Startup And Application Shell

- Show a splash screen while starting.
- Apply the configured theme on startup.
- Initialize the database on startup.
- Show startup progress messages.
- Set application/window icons from bundled resources when available.
- Center application windows on screen.

## Persistence And Data Model

- Store projects.
- Store participants.
- Store documents.
- Store nodes.
- Store coded segments.
- Store document source metadata.
- Maintain node parent IDs and positions.
- Maintain coded segment offsets.
- Support database schema initialization and migration.
- Create database backups.
- Invalidate analysis/dashboard cache when project data changes.

## Packaging And Distribution

- Run from source on macOS with `scripts/start-nodeflow.sh`.
- Run from source on Windows with `scripts/start-nodeflow.ps1`.
- Build macOS app bundles with `scripts/package-nodeflow.sh`.
- Build Windows executables with `scripts/package-nodeflow.ps1`.
- Package with PyInstaller.
- Use platform-specific builds rather than cross-packaging.

## Testing And Developer Utilities

- Run tests with `pytest`.
- Includes unit tests for repositories, dashboard calculations, exports, imports, settings, segment rebasing, and workspace history.
- Includes a script to create an export demo project with participants, nodes, documents, and coded segments.
- Includes logging configuration for app startup and operations.
