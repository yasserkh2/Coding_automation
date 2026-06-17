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
  - `config.yml` stores shared project, graph, global Codex defaults, and
    per-node Codex model overrides.
  - `graph/` contains a LangGraph workflow for new-project and enhance-project work.
  - New-project setup creates `Current_Task.md`, `Done_AI_Tasks.md`, and
    `business requirements.md` before the first Codex implementation call.
  - The enhance-project route prepares task handoff docs, then routes directly
    into AI skill orchestration.
  - `create_enhance_project_docs` asks Codex to inspect the existing project,
    read `Done_AI_Tasks.md`, and write the active handoff to `Current_Task.md`.
  - The AI orchestrator can route enhancement work to backend, frontend, system
    designer, data analysis, ML data preparation, model training, or model
    evaluation skill nodes using an explicit skill request, an agent named in
    the task text, or an LLM-backed classifier.
  - Skill nodes chat with Codex, then either continue their bounded Codex turns,
    ask for human input, or end successfully.
  - `graph.cli` logs every graph node as it runs and logs the full prompt sent to
    Codex before each Codex CLI call.
  - `pyproject.toml` defines the package metadata and script entry points.
  - `tests/` contains unit tests for the package and graph structure.

  Not built yet:

  - Full LangGraph manager agent.
  - Real implementations behind the backend, frontend, system designer, data
    analysis, ML data preparation, model training, and model evaluation skill
    nodes.
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
    Rendered image of the current LangGraph workflow, including optional
    skill-to-agent-status and skill-to-human-review routes.

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

  Shared project defaults live in `config.yml`. Codex settings, graph route names,
  default project paths, and `graph.skill_max_turns` are loaded from this file. Do
  not put API keys or secrets there.

  Codex model settings can be configured globally and then overridden per graph
  node. Each node override inherits missing values from the global `codex` block:

  ```yaml
  codex:
    model_provider: openrouter
    model: openai/gpt-5.4-mini
    provider_name: OpenRouter
    base_url: https://openrouter.ai/api/v1
    env_key: OPENROUTER_API_KEY
    timeout_seconds: 1800
    reasoning_effort: minimal
    nodes:
      implement_new_project:
        model: openai/gpt-5.4-mini
        reasoning_effort: minimal
      create_enhance_project_docs:
        model: openai/gpt-5.4-mini
        reasoning_effort: minimal
      ai_orchestrator:
        model: openai/gpt-5.4-mini
        reasoning_effort: minimal
      backend:
        model: openai/gpt-5.4-mini
        reasoning_effort: minimal
      frontend:
        model: openai/gpt-5.4-mini
        reasoning_effort: minimal
      system_designer:
        model: openai/gpt-5.4-mini
        reasoning_effort: minimal
      data_analysis:
        model: openai/gpt-5.4-mini
        reasoning_effort: minimal
      ml_data_preparation:
        model: openai/gpt-5.4-mini
        reasoning_effort: minimal
      model_training:
        model: openai/gpt-5.4-mini
        reasoning_effort: minimal
      model_evaluation:
        model: openai/gpt-5.4-mini
        reasoning_effort: minimal
      compact_conversation:
        model: openai/gpt-5.4-mini
        reasoning_effort: minimal
  ```

  You can override any Codex setting per node, including `model_provider`,
  `model`, `provider_name`, `base_url`, `env_key`, `timeout_seconds`, and
  `reasoning_effort`. Supported reasoning effort values are `minimal`, `low`,
  `medium`, and `high`. The `compact_conversation` node is the LLM used when
  skill-chat history exceeds the configured compaction threshold.

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
  `.env.example`, `config.yml`, `requirements.txt`, `.gitignore`, and `README.md`, then sends
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
    -c model='openai/gpt-5.4-mini' \
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
  .env.example
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
    -> ai_orchestrator
        -> backend
        -> frontend
        -> system_designer
        -> data_analysis
        -> ml_data_preparation
        -> model_training
        -> model_evaluation
        -> END or human_in_the_loop
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

  `ai_orchestrator` chooses a skill route from two signals. First, it uses an
  explicit request: `requested_skill` from the API/CLI, or a named agent in the
  task text such as `frontend agent`, `backend agent`, `system designer agent`,
  `data analysis agent`, `ml data preparation agent`, `model training agent`,
  or `model evaluation agent`. If no agent is explicitly requested, it delegates
  to the LLM-backed skill classifier:

  ```text
  backend
  frontend
  system_designer
  data_analysis
  ml_data_preparation
  model_training
  model_evaluation
  ```

  The classifier prompt lives in `graph/prompts.json`, and the allowed skill list
  is filled from the skill nodes currently wired in `graph/workflow.py`.

  If the classifier is unavailable or returns an invalid route, the workflow
  defaults to `system_designer`.

  The skill nodes run bounded Codex conversations. Each skill node builds a
  lane-specific `skill_prompt` from `graph/prompts.json`, sends it to Codex, and
  stores the latest response plus a transcript in graph state. The prompt scopes
  the work to the selected lane:

  ```text
  backend          APIs, endpoints, auth, persistence, services, backend config
  frontend         screens, components, forms, layout, styling, client behavior
  system_designer  architecture, module boundaries, data flow, contracts, risks
  data_analysis    Data Understanding & Analysis in notebooks for datasets and ML models
  ml_data_preparation  Cleaning, preprocessing, feature/label prep, and leakage-safe ML splits
  model_training   Reproducible baselines, training runs, tuning, and fitted model artifacts
  model_evaluation Metrics, error analysis, comparison, thresholds, calibration, and reports
  ```

  Skill conversations run as a bounded ReAct-agent loop instead of a one-shot
  implementation prompt. Each skill turn asks Codex to observe the relevant task
  and project state, focus on one task-specific requirement, act with the smallest
  useful edit/verification/handoff update, report the result, then decide whether
  to continue, finish with audit, or ask for human review.

  Each skill prompt also receives project software context before it starts:
  project structure, `git status --short`, `git diff --stat`, and a capped
  `git diff`. Follow-up turns rebuild that context after every Codex response, so
  the next turn sees the latest code edits/diffs made by the previous run. This
  context is a starting map only; Codex is still expected to inspect the project
  files directly before editing.

  After a selected skill finishes successfully, the graph ends. A skill can
  still route to `human_in_the_loop` by asking Codex to return
  `SKILL_STATUS: human_review` with a `QUESTION: ...` line.

  Skill conversations are bounded by `graph.skill_max_turns` in `config.yml`. The
  default is 3 Codex turns per selected skill: enough for observation/focus,
  focused action, and one extra continue/audit turn when needed. You can override
  it per CLI run with `--skill-max-turns`.

  The compact conversation feature is controlled by
  `graph.compact_conversation_tokens`, defaulting to roughly 10,000 tokens. Below
  that threshold, follow-up turns receive the full skill chat history. Above it,
  the graph asks the configurable `compact_conversation` LLM node to compact the
  history before building the next follow-up prompt. You can override the
  threshold per CLI run with `--compact-conversation-tokens`.
  Skill prompts ask Codex to end each response with one of three status lines:

  ```text
  SKILL_STATUS: done          end the task successfully
  SKILL_STATUS: continue      ask Codex for another skill turn
  SKILL_STATUS: human_review  pause at human_in_the_loop with QUESTION
  ```

  The graph stops the skill conversation at `done`, `human_review`, a missing
  `continue` status, or the maximum turn count.
  Before a skill can return `SKILL_STATUS: done`, its prompt requires a completion
  audit of the project handoff and config files. The skill must check and update
  `README.md`, `Done_AI_Tasks.md`, `Current_Task.md`, `.env` placeholders,
  `.env.example`, `config.yml`, dependency files, and `.gitignore` when the task
  affects them, or explicitly say they were checked and did not need changes.
  The graph also enforces this: if Codex returns `SKILL_STATUS: done` without
  clearly confirming the audit files, the skill sends one focused audit prompt
  before accepting completion.
  The first skill prompt includes prior skill/Codex chat history in role-style
  form when it exists. Follow-up turns use full skill chat history until the
  compact conversation threshold is exceeded. After that, they send compacted
  memory produced by the configurable `compact_conversation` LLM node and tell
  Codex to use that memory together with fresh project software context,
  `Current_Task.md`, `Done_AI_Tasks.md`, and project files as the source of truth.

  ```text
  skill:
  <previous skill prompt or follow-up>

  codex:
  <previous Codex response>
  ```

  The same role-style transcript is saved under the project `Chats_History/`
  directory after each skill run so the conversation can be reviewed later. Each
  skill session gets a new timestamped file, for example
  `Chats_History/backend_20260615T123456123456Z.md`.

  `create_enhance_project_docs` also keeps its Codex message concise. It asks
  Codex to inspect only files relevant to the incoming task, use done-task history
  only when helpful, and write a focused `Current_Task.md` instead of a generic
  handoff.

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
  python3 -m graph.cli --task "# Task
  Create a file named hello.md with a short greeting." --project-dir ./projects/demo --project-name demo --task-status new --business-requirement "Build the first version of the demo project."
  ```

  When running from the repo virtual environment, use:

  ```bash
  .venv/bin/python -m graph.cli --task "# Task
  Create a file named hello.md with a short greeting." --project-dir ./projects/demo --project-name demo --task-status new --business-requirement "Build the first version of the demo project."
  ```

  If the package is installed, you can use the console script:

  ```bash
  coding-graph --task "# Task
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

  From the terminal, `--task` is required and starts the enhancement process:

  ```bash
  .venv/bin/python -m graph.cli --task "# Task
  Add a FastAPI backend skeleton for the Andalusia call center chatbot." \
    --task-status enhance \
    --project-dir "/home/Yasser.hamed/Downloads/andalusia-chatbot" \
    --requested-skill backend
  ```

  The enhance path runs `create_enhance_project_docs` before routing to the skill
  node. That node asks Codex to inspect the project, read `Done_AI_Tasks.md`, and
  write the prepared implementation handoff to `Current_Task.md`.

  The default maximum skill/Codex conversation length is configured in
  `config.yml`:

  ```yaml
  graph:
    skill_max_turns: 3
    compact_conversation_tokens: 10000
  ```

  To override it for one run, set `--skill-max-turns` or
  `--compact-conversation-tokens`:

  ```bash
  .venv/bin/python -m graph.cli --task "# Task
  Add a FastAPI backend skeleton for the Andalusia call center chatbot." \
    --task-status enhance \
    --project-dir "/home/Yasser.hamed/Downloads/andalusia-chatbot" \
    --requested-skill backend \
    --skill-max-turns 3 \
    --compact-conversation-tokens 10000
  ```

  You can force a skill route:

  ```bash
  python3 -m graph.cli --task "# Task
  Polish the dashboard layout." \
    --project-dir ./projects/demo \
    --requested-skill frontend
  ```

  For notebook-based Data Understanding & Analysis:

  ```bash
  python3 -m graph.cli --task "# Task
  Create an exploratory data analysis notebook for the training dataset." \
    --project-dir ./projects/demo \
    --requested-skill data_analysis
  ```

  For ML data preparation:

  ```bash
  python3 -m graph.cli --task "# Task
  Clean and preprocess the training data, then create leakage-safe train/validation/test splits." \
    --project-dir ./projects/demo \
    --requested-skill ml_data_preparation
  ```

  For model training:

  ```bash
  python3 -m graph.cli --task "# Task
  Train a baseline model from the prepared dataset and save the fitted artifact." \
    --project-dir ./projects/demo \
    --requested-skill model_training
  ```

  For model evaluation:

  ```bash
  python3 -m graph.cli --task "# Task
  Evaluate the trained model on the held-out test set and write an evaluation report." \
    --project-dir ./projects/demo \
    --requested-skill model_evaluation
  ```

  ### CLI logs

  `graph.cli` logs progress to the terminal. Each graph node prints a
  `<node_name>: running` line when it starts, followed by a short detail line for
  the work it is doing. Every node that sends a message to Codex is also tagged in
  the Codex conversation logs. The service logs the full prompt and final response,
  and the runner streams Codex stdout/stderr in real time while the CLI process is
  still running.

  Example:

  ```text
  INFO graph.nodes: enhance_project: running
  INFO graph.nodes: create_enhance_project_docs: running
  INFO graph.nodes: create_enhance_project_docs: asking Codex to inspect project and write Current_Task.md
  INFO codex.service: codex_service[create_enhance_project_docs]: sending prompt to Codex project_dir=/home/Yasser.hamed/Downloads/andalusia-chatbot sandbox=workspace-write full_env=False prompt_chars=...
  INFO codex.service: codex_service[create_enhance_project_docs] >>> prompt:
  Prepare the enhancement handoff for this existing project.
  ...
  INFO codex.runner: codex_cli[create_enhance_project_docs]: starting project_dir=/home/Yasser.hamed/Downloads/andalusia-chatbot sandbox=workspace-write timeout_seconds=...
  INFO codex.runner: codex_cli[create_enhance_project_docs] stdout: Reading project files...
  INFO codex.runner: codex_cli[create_enhance_project_docs] stdout: Updated Current_Task.md.
  INFO codex.service: codex_service[create_enhance_project_docs] <<< response:
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

  Check the exact model slug in OpenRouter if `openai/gpt-5.4-mini` stops working or is not available on the account.
