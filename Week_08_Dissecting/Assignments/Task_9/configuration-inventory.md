# Copilot Workspace Configuration

GitHub Copilot in VS Code stores these workspace customizations in separate files rather than one profile or system-prompt configuration file. The files below are the configuration created or used during the assignments:

| Customization | File | Purpose |
|---|---|---|
| Workspace-wide rule | [AGENTS.md](../../../AGENTS.md) | Requires new generated files to identify the creating agent and model. |
| Task-specific instructions | [Task 3 AGENTS.md](../Task_3/AGENTS.md) | Guidance scoped to the Task 3 folder. |
| Custom prompt | [Answer.prompt.md](../../../.github/prompts/Answer.prompt.md) | Reusable `/Answer` prompt. |
| Custom skill/command | [new-command SKILL.md](../../../.github/skills/new-command/SKILL.md) | Defines the `/new-command` skill; automatic model invocation is disabled. |
| Custom skill/command | [test SKILL.md](../../../.github/skills/test/SKILL.md) | Defines the user-invocable `/test` skill. |
| Additional workspace skill | [architecture-proposal-adr SKILL.md](../../../.github/skills/architecture-proposal-adr/SKILL.md) | Architecture proposal and ADR workflow. |
| MCP server configuration | [`.mcp.json`](../../../.mcp.json) | Registers the local `task7-demo` server and its `add` tool. |

The MCP configuration uses a machine-specific Python executable path, so it may need to be updated on another computer. It contains no API key or other service credential. Copilot's protected core system prompt is not included because it is not exposed as an editable workspace configuration file.

<!-- Created by: AI assistant using Copilot SDK in VS Code. Model: not exposed in this session. -->
