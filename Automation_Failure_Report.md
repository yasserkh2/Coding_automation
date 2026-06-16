# Automation Failure Report

## Purpose

This report records the current failure discussion for the coding automation
project. It should be used as design input before adding more agents, ML
pipelines, AI-engineering workflows, or Codex orchestration features.

The core lesson is simple: the system should not only call Codex to write code.
It must supervise software work with clear requirements, project understanding,
verification, review, and evidence.

## Current Target

The project is intended to automate repetitive cycles for ML and AI engineers,
including:

- Software implementation tasks.
- ML pipeline setup and enhancement.
- Data processing and validation workflows.
- Training, evaluation, and experiment cycles.
- Prompt, RAG, agent, and model-configuration workflows.
- Deployment, smoke testing, and handoff documentation.

However, the system is currently not producing good software consistently. This
must be fixed before expanding deeply into ML/AI-specific automation.

## Observed Failure

The current workflow is too close to:

```text
task -> route to agent -> ask Codex to write code -> accept text response as done
```

This produces weak results because the system does not strongly enforce the
normal software engineering loop:

```text
understand -> design -> plan -> implement -> run -> inspect failures -> fix -> review -> document
```

For ML and AI engineering, this gap becomes worse because "done" requires proof:
pipelines must run, data must validate, evaluations must be recorded, prompts
must be tested, and model or agent behavior must be checked against examples.

## Main Failure Causes

### 1. Weak specification step

The system does not reliably convert a user task into a precise implementation
contract. A good task handoff should include:

- Goal.
- Scope.
- Non-goals.
- Expected files or modules.
- Acceptance criteria.
- Verification commands.
- Risks and assumptions.

Without this, Codex can easily overbuild, underbuild, or solve the wrong
problem.

### 2. Weak project understanding

Before implementation, the system should build a reliable profile of the target
project:

- Language and framework.
- App or package structure.
- Existing conventions.
- Test commands.
- Run commands.
- Important config files.
- Existing architecture boundaries.
- Current git status and changed files.

The current workflow includes some project context, but it is not treated as a
mandatory artifact or quality gate.

### 3. No strong acceptance criteria

The system currently relies too much on the model saying it is done. Good
software requires explicit acceptance checks, such as:

- Tests pass.
- App starts.
- Pipeline runs.
- API contract is satisfied.
- Output format is valid.
- Existing behavior is preserved.
- Requested behavior is demonstrated.

### 4. No reliable verification loop

The system should run commands, capture failures, and route back to a fixer when
verification fails.

Expected loop:

```text
coder -> verifier -> fixer -> verifier -> reviewer -> done
```

The current workflow does not make this loop central enough.

### 5. No independent reviewer node

The same model path that writes the code is too close to the path that accepts
completion. A reviewer node should check the result independently and reject
weak output.

The reviewer should ask:

- Did the requested behavior actually get implemented?
- Did the project still run?
- Did tests pass?
- Were unrelated files changed?
- Were docs updated appropriately?
- Is the solution consistent with the existing architecture?
- Are there missing edge cases?
- Is the final handoff honest about what was and was not verified?

### 6. Skill lanes are too generic

Current lanes such as backend, frontend, and system designer are useful for
ordinary app work, but they are not enough for AI/ML engineering automation.

The system eventually needs more specific lanes, such as:

- Data engineer.
- ML pipeline engineer.
- Model/training engineer.
- Evaluation engineer.
- Prompt engineer.
- Agent engineer.
- RAG engineer.
- Deployment engineer.
- Reviewer/verifier.

But these should be added after the base software quality loop is stronger.

### 7. Done criteria are text-based, not evidence-based

The system should not accept completion only because a response contains a
status marker like `SKILL_STATUS: done`.

Completion should require evidence artifacts:

- Commands run.
- Results captured.
- Files changed.
- Tests passed or failed.
- Known limitations.
- Follow-up tasks.

## Required Product Reframe

The project should become an AI software engineer supervisor, not only a Codex
wrapper.

Codex can still be the implementation engine, but the graph should behave like a
senior engineer supervising the work:

- Clarify the task.
- Understand the repo.
- Create an implementation plan.
- Restrict scope.
- Run verification.
- Inspect failures.
- Route retries.
- Review quality.
- Produce an honest final handoff.

## Proposed Core Workflow

Before adding more ML/AI-specific agents, implement this stronger software
workflow:

```text
user task
  -> project_scanner
  -> task_planner
  -> implementation_agent
  -> verification_agent
  -> fix_agent, if verification fails
  -> review_agent
  -> final_handoff
```

## Proposed Core Artifacts

The workflow should create or update these artifacts:

```text
Project_Profile.md
Implementation_Plan.md
Acceptance_Criteria.md
Verification_Report.md
Review_Report.md
Done_AI_Tasks.md
Current_Task.md
```

For AI/ML projects, later extensions may add:

```text
AI_Project_Profile.md
ML_Project_Profile.md
Pipeline_Manifest.yml
Experiment_Report.md
Evaluation_Report.md
Prompt_Catalog.md
Eval_Cases.yml
Agent_Trace_Report.md
RAG_Quality_Report.md
Model_Config_Record.md
```

## Definition Of Good Software For This System

The system should consider software work good only when:

- The requested behavior is implemented.
- The change is minimal and scoped.
- The code follows the existing project structure and style.
- The app, package, pipeline, or relevant subsystem can run.
- Tests, smoke checks, or clear verification commands are executed.
- Failures are captured and acted on.
- Documentation is updated when useful.
- The final handoff lists changed files and verification results.
- Unverified items are clearly marked as unverified.

## Near-Term Priorities

1. Add a `project_scanner` node.
2. Add a `task_planner` node that writes acceptance criteria.
3. Add a `verification_agent` node that runs or requests concrete checks.
4. Add a `review_agent` node that can reject incomplete work.
5. Add a retry route from verification or review back to implementation.
6. Change done criteria from text status to evidence-based reports.
7. Only after this, add ML/AI-specific engineering lanes.

## Strategic Note

The project should not rush into many specialized agents before the base
engineering loop is reliable. More agents will not fix weak supervision. The
first goal is to make the system produce consistently good software with proof.

After that foundation is solid, ML and AI engineering automation can be layered
on top with specialized artifacts, evaluation flows, and pipeline-aware
verification.
