# Coding Automation

This project is the start of an AI coding automation system.

The plan is to use a manager agent to plan software work, then delegate code-writing tasks to **Codex CLI**. Codex CLI will write files into a local project folder, and Cursor or VS Code will open the same folder for review, editing, running, and Git work.

## Planned Architecture

```text
User request
  -> LangGraph / LangChain manager agent
  -> Codex CLI tool wrapper
  -> codex exec
  -> OpenRouter
  -> coding model
  -> local project files
  -> Cursor / VS Code
  -> Git
```

## Why Codex CLI

We are using **Codex CLI**, not the Codex SDK.

Codex CLI is easier to test, script, and connect to a manager agent. The Python package in `codex/` calls `codex exec` through `subprocess`, so LangGraph or LangChain can treat Codex like a normal tool.

The code is kept directly in this project folder:

```text
codex/
  __init__.py     Public package exports.
  binary.py       Finds a usable Codex CLI binary and avoids the broken Snap binary when possible.
  cli.py          One-shot CLI entry point.
  config.py       Stores immutable OpenRouter/Codex settings.
  environment.py  Loads .env values.
  ports.py        Interface that graph code should depend on.
  project_config.py
                  Loads config.yml and merges it with built-in defaults.
  runner.py       Builds and runs codex exec commands.
  service.py      High-level speak_with_codex() function and CodexService class.
  terminal.py     Terminal prompt app.

graph/
  LangGraph coding workflow for new-project and enhance-project paths.
```

## Current Status

Working:

- Codex CLI is installed.
- OpenRouter is configured as the Codex model provider.
- `.env` is used for `OPENROUTER_API_KEY`.
- The smoke test succeeded with `OK`.
- The structured `codex/` package successfully called Codex CLI through OpenRouter.
- `scripts/talk-to-codex-openrouter.sh` starts an interactive Codex CLI session with OpenRouter config.
- `scripts/create-project-with-codex.sh` creates project folders under `projects/` and sends prompts to Codex CLI.
- `--full-access` mode is available for local developer-style access.
- `config.yml` stores shared project, graph, and Codex defaults.
- `graph/` contains a starter LangGraph workflow that calls the Codex adapter.
- The enhance-project route now prepares task handoff docs, records agent status,
  and routes to either human review or AI skill orchestration.
- The AI orchestrator can route enhancement work to backend, frontend, or system
  designer skill nodes.
- `pyproject.toml` defines the package metadata and script entry points.
- `tests/` contains unit tests for the package and graph structure.

Not built yet:

- Full LangGraph manager agent.
- Real implementations behind the backend, frontend, and system designer skill nodes.
- A2A server/client layer.
- Task queue.
- Git branch/commit automation.
- Cursor/VS Code workflow automation.
- Multi-agent review flow with Claude, Gemini, or another model.

## Files

```text
.env
  Stores OPENROUTER_API_KEY locally.

config.yml
  Active non-secret defaults loaded by Codex and LangGraph code.

scripts/test-codex-openrouter.sh
  Small smoke test. It asks Codex to reply OK only.

scripts/codex_cli_tool.py
  Backward-compatible entry point that re-exports the package functions.

codex/
  Codex CLI adapter package.

graph/
  LangGraph workflow package.

graph/prompts.json
  Central prompt and message template catalog used by graph nodes.

graph.png
  Rendered image of the current LangGraph workflow.

tests/
  Unit tests for binary resolution, command construction, and graph workflow.

scripts/talk-to-codex-openrouter.sh
  Interactive Codex CLI launcher that loads .env and uses OpenRouter.

scripts/write-with-codex-cli.sh
  Shell helper for asking Codex CLI to write code in this folder.

scripts/create-project-with-codex.sh
  Creates a project folder under projects/ and asks Codex CLI to work there.

scripts/speak-with-codex.py
  Terminal prompt wrapper around speak_with_codex().

requirements.txt
  Python dependencies for the Codex adapter, YAML config loading, and LangGraph workflow.

pyproject.toml
  Python project metadata, optional dev dependency, and console script definitions.

projects/
  Generated apps/projects live here. Ignored by Git.

.codex-home/
  Local Codex state and project Codex config. Ignored by Git.
```

## Setup

Put your OpenRouter key in `.env`:

```bash
OPENROUTER_API_KEY="sk-or-xxxxx"
```

The `.env` file is ignored by Git.

Shared project defaults live in `config.yml`. Codex settings, graph route names, and default project paths are loaded from this file. Do not put API keys or secrets there.

Create a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

If venv creation fails with `ensurepip is not available`, install the Ubuntu venv package:

```bash
sudo apt update
sudo apt install python3.12-venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Test The Integration

Run:

```bash
./scripts/test-codex-openrouter.sh
```

Expected result:

```text
OK
```

You can also test the Python wrapper:

```bash
python3 -m codex.cli "Reply with OK only." --sandbox read-only
```

Expected result:

```text
OK
```

## Write Code With Codex CLI

Run:

```bash
./scripts/write-with-codex-cli.sh "Create a small Python CLI app here with tests and a README."
```

Or call the wrapper directly:

```bash
python3 -m codex.cli "Create a small Python CLI app here with tests and a README."
```

## Talk To Codex CLI Interactively

Run:

```bash
./scripts/talk-to-codex-openrouter.sh
```

This starts the interactive Codex CLI with `.env` loaded and OpenRouter configured.

Use this script instead of plain `codex`. Plain `codex` may default to the OpenAI API endpoint and fail with an OpenRouter key.

## Create A New Project Folder

Use this helper to create a project under `projects/` and send the prompt to Codex CLI:

```bash
./scripts/create-project-with-codex.sh todo-app "Create a Python Flask todo app with tests and a README."
```

This creates:

```text
projects/todo-app/
```

Then Codex CLI works inside that folder.

For the graph-driven new-project flow, use `task_status="new"` or
`--task-status new`. The new-project route creates or verifies the named
project folder, writes `Current_Task.md`, `Done_AI_Tasks.md`, and
`business requirements.md`, initializes git, creates `.venv`, `.env`,
`config.yml`, `requirements.txt`, `.gitignore`, and `README.md`, then sends
Codex a focused implementation prompt.

For full local developer access, use:

```bash
./scripts/create-project-with-codex.sh --full-access fullstack-app "Create a full-stack app, install dependencies, run tests, and fix any failures."
```

`--full-access` runs Codex CLI with:

```text
--sandbox danger-full-access
-c shell_environment_policy.inherit=all
```

Use this only when you trust the prompt and target folder, because Codex can run broader commands with your local environment.

You can also call the Python wrapper directly with full access:

```bash
python3 -m codex.cli \
  "Create a full-stack app, install dependencies, run tests, and fix failures." \
  --project-dir "./projects/fullstack-app" \
  --sandbox danger-full-access \
  --full-env
```

The wrapper uses this Codex CLI shape:

```bash
codex exec \
  --sandbox workspace-write \
  --cd "$PROJECT_DIR" \
  -c model_provider=openrouter \
  -c model='openai/gpt-5-codex' \
  -c model_providers.openrouter.name=OpenRouter \
  -c model_providers.openrouter.base_url='https://openrouter.ai/api/v1' \
  -c model_providers.openrouter.env_key=OPENROUTER_API_KEY \
  "$PROMPT"
```

For full access, the wrapper also adds:

```text
--sandbox danger-full-access
-c shell_environment_policy.inherit=all
```

## Troubleshooting

### Missing OpenRouter Key

If Codex says:

```text
Missing environment variable: `OPENROUTER_API_KEY`.
```

Start Codex with:

```bash
./scripts/talk-to-codex-openrouter.sh
```

That script loads `.env` before starting Codex.

### OpenAI 401 With An OpenRouter Key

If Codex says:

```text
Incorrect API key provided: sk-or-...
url: https://api.openai.com/v1/responses
```

Then Codex is using the OpenAI API endpoint, not OpenRouter. Exit that session and start a new one with:

```bash
./scripts/talk-to-codex-openrouter.sh
```

The expected OpenRouter base URL is:

```text
https://openrouter.ai/api/v1
```

### Snap/AppArmor Error

If `codex` fails with:

```text
snap-confine has elevated permissions and is not confined but should be.
Please make sure that the snapd.apparmor service is enabled and started.
```

Fix Snap/AppArmor:

```bash
sudo systemctl enable --now snapd.apparmor
codex --version
```

### Codex CLI Is Not A Pip Requirement

`requirements.txt` is only for Python packages. Codex CLI is an external command, so check it with:

```bash
codex --version
```

## LangGraph Workflow

The starter graph begins with `project_router`. It routes by `task_status`.
New-project tasks run:

```text
new_project
  -> create_project_dir
  -> create_project_docs
  -> initialize_git
  -> initialize_venv
  -> create_environment_files
  -> implement_new_project
  -> finalize_new_project
```

`implement_new_project` is the only Codex call in this branch. It asks Codex
to update `Done_AI_Tasks.md` with a concise summary before finishing. The
`finalize_new_project` node is local; it records the graph setup summary in
`Done_AI_Tasks.md` without starting another Codex session.

All nodes before `implement_new_project` are local Python setup nodes. They do
not talk to Codex. The new-project branch sends exactly one filled prompt to
Codex, containing:

```text
project_name
project_dir
completed setup steps
business_requirement
Current_Task.md
instructions to update Done_AI_Tasks.md before finishing
```

The local setup nodes create this baseline environment:

```text
Current_Task.md
Done_AI_Tasks.md
business requirements.md
.git/
.venv/
.env
config.yml
requirements.txt
.gitignore
README.md
```

Codex is instructed not to create extra directories, packages, apps, tests, or
project files unless `Current_Task.md` explicitly asks for them. If
`Current_Task.md` only asks to initialize the environment, Codex should stop
after verifying and updating the prepared files.

Enhancement tasks run through a separate path:

```text
enhance_project
  -> create_enhance_project_docs
  -> agent_status
      -> human_in_the_loop
      -> ai_orchestrator
          -> backend
          -> frontend
          -> system_designer
```

`create_enhance_project_docs` requires an existing project directory. It seeds
`Done_AI_Tasks.md` from existing done-task history, falling back to legacy
`Ai_Task.md` content when needed, then asks Codex to inspect the project, read
the done-task history, and write the active implementation handoff to
`Current_Task.md`:

```text
Done_AI_Tasks.md
<previous done-work summary, legacy Ai_Task.md content, or a fallback if missing>

Current_Task.md
# Current Task

<Codex-prepared task to implement>
```

`agent_status` records the current graph status and chooses whether to continue
to `ai_orchestrator` or pause at `human_in_the_loop`. By default, enhancement
work continues to the AI orchestrator. Use `needs_human_review=True` or
`--needs-human-review` to route to human review.

`ai_orchestrator` chooses a skill route. It uses `requested_skill` when
provided, otherwise it inspects the new task description and routes by simple
keywords:

```text
backend          API, database, server, endpoint, auth, login, model, migration
frontend         UI, CSS, HTML, component, page, screen, button, form
system_designer  architecture, design, system, plan, schema, workflow, or unclear tasks
```

The skill nodes are placeholders right now. They mark the selected lane in
graph state and are ready for real Codex-backed skill behavior later.

Graph prompt text is centralized in `graph/prompts.json`. Nodes load templates
through `graph.prompt_catalog.render_prompt()`, so prompt wording can be tuned
without rewriting workflow logic.

```python
from graph import run_coding_graph


result = run_coding_graph(
    "# Task\nCreate a file named hello.md with a short greeting.",
    project_dir="./projects/demo",
    project_name="demo",
    task_status="new",
    business_requirement="Build the first version of the demo project.",
    full_access=True,
)

print(result["response"])
```

You can also run it from the terminal:

```bash
python3 -m graph.cli "# Task
Create a file named hello.md with a short greeting." --project-dir ./projects/demo --project-name demo --task-status new --business-requirement "Build the first version of the demo project."
```

When running from the repo virtual environment, use:

```bash
.venv/bin/python -m graph.cli "# Task
Create a file named hello.md with a short greeting." --project-dir ./projects/demo --project-name demo --task-status new --business-requirement "Build the first version of the demo project."
```

If the package is installed, you can use the console script:

```bash
coding-graph "# Task
Create a file named hello.md with a short greeting." --project-dir ./projects/demo --project-name demo --task-status new --business-requirement "Build the first version of the demo project."
```

Use `--config ./path/to/config.yml` to run the graph with another YAML config file.

For an enhancement, use `task_status="enhance"` or omit `--task-status`, and `business_requirement` can be empty if the project already has it saved.

```python
from graph import run_coding_graph


result = run_coding_graph(
    "# Task\nAdd login API endpoints.",
    project_dir="./projects/demo",
    task_status="enhance",
)

print(result["skill_route"])
```

From the terminal, the first positional argument is the new task input that
starts the enhancement process:

```bash
.venv/bin/python -m graph.cli "# Task
Add a FastAPI backend skeleton for the Andalusia call center chatbot." \
  --task-status enhance \
  --project-dir "/home/Yasser.hamed/Downloads/andalusia-chatbot" \
  --requested-skill backend
```

The enhance path runs `create_enhance_project_docs` before routing to the skill
node. That node asks Codex to inspect the project, read `Done_AI_Tasks.md`, and
write the prepared implementation handoff to `Current_Task.md`.

You can force a skill route:

```bash
python3 -m graph.cli "# Task
Polish the dashboard layout." \
  --project-dir ./projects/demo \
  --requested-skill frontend
```

You can pause for human review before AI orchestration:

```bash
python3 -m graph.cli "# Task
Review the database migration plan." \
  --project-dir ./projects/demo \
  --needs-human-review
```

### CLI logs

`graph.cli` logs progress to the terminal. Each graph node prints a
`<node_name>: running` line when it starts, followed by a short detail line for
the work it is doing. Before each Codex CLI call, the runner also logs the
project directory, sandbox, timeout, and the full prompt being sent to Codex.

Example:

```text
INFO graph.nodes: enhance_project: running
INFO graph.nodes: create_enhance_project_docs: running
INFO graph.nodes: create_enhance_project_docs: asking Codex to inspect project and write Current_Task.md
INFO codex.runner: codex_cli: starting project_dir=/home/Yasser.hamed/Downloads/andalusia-chatbot sandbox=workspace-write timeout_seconds=...
INFO codex.runner: codex_cli: prompt sent to Codex:
Prepare the enhancement handoff for this existing project.
...
```

For lower-level control, import `run_codex_cli`:

```python
from codex import run_codex_cli

result = run_codex_cli(
    "Build the backend API in this repo.",
    project_dir="/path/to/project",
)
```

Quick function test:

```bash
python3 -c "from codex import CodexBinaryResolver, speak_with_codex; print('BIN', CodexBinaryResolver().resolve()); print(speak_with_codex('Reply with OK only.', project_dir='.', full_access=False))"
```

Expected result:

```text
BIN /path/to/codex
OK
```

To type the function prompt directly in the terminal, run:

```bash
python3 scripts/speak-with-codex.py --project-dir "./projects/demo" --full-access
```

Then type your prompt and press `Enter`.

For multi-line prompts, run:

```bash
python3 scripts/speak-with-codex.py --project-dir "./projects/demo" --full-access --multi-line
```

Then type your prompt and press `Ctrl+D` when finished.

## Tests

Run:

```bash
.venv/bin/python -m pytest
```

Expected result:

```text
14 passed, 1 subtests passed
```

The manager agent should be responsible for:

- breaking the user request into coding tasks
- choosing the target project directory
- calling Codex CLI for implementation
- asking another model to review the result
- running tests
- committing changes to Git after review

## Next Steps

1. Add planner and reviewer nodes to the LangGraph workflow.
2. Add a reviewer tool, probably Claude or Gemini through OpenRouter.
3. Add test-running and Git commit tools.
4. Add a task queue.
5. Add an A2A layer if we want other agents to call this system.

## Notes

Check the exact model slug in OpenRouter if `openai/gpt-5-codex` stops working or is not available on the account.
