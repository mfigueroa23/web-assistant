# AGENTS.md — web-assistant
API Rest of a virtual assistan that use LangChain to orchestrate agents
using alembic for database migrations and FastAPI as the api framework.

## Comandos
- `uv run fastapi dev`: Starts the server in development mode.
- `uv run pytest`: Runs the tests.
- `uv run alembic revision --autogenerate -m <"mensaje">`: Creates a new migration.
- `uv run alembic check`: Verifies the migrations.
- `uv run alembic upgrade head`: Applies the latest migration.
- `uv run pyright`: Lints the code.

## Documentation rules
- The project has a knowledge base in JIRA and Confluence under the key `VTA`, and the user must review any
  resource before it is created in JIRA or Confluence.
- A request for new development must be turned into user stories (there can be more than 1) in JIRA
  following this format (`[]` must be lists):
  ```
  As a <role> I want <feature> so that <benefit>

  ## Acceptance criteria
  [] <acceptance criterion 1>
  [] <acceptance criterion N>
  ```
- A user story must have these ticket properties:
  - Priority
  - Label (e.g. `web`, `whatsapp`, `google`, etc.) - it can have more than 1, plus the system it belongs to
  - Start date and due date (estimated)
  - Story points (estimated) following the [Fibonacci](https://en.wikipedia.org/wiki/Fibonacci_sequence) method
- When asked to document in Confluence, use the templates available in the `VTA` space:
  - `How to`: Documentation of processes and procedures
  - `Troubleshooting`: Documentation of problems and solutions

## Development rules
- Code written in English
- Module-based project architecture
- Simple code without complex logic; when needed, split it into small, reusable functions
- Do not add external dependencies without the developer's prior approval
- Do not build Docker images without the developer's prior approval
- A user story is split into tasks, and each task must be a small, working and verifiable piece of code
- A task related to a ticket must be done on a branch named `<type>/<JIRA-KEY-TICKET>-<description>`, e.g. `feature/PRT-1234-add-new-endpoint`
- Before writing the code, write the tests for the small verifiable tasks, following TDD (Test Driven Development)
- When a small task is finished, wait for the developer's approval before committing, in English, without
  co-authorship from any AI, following [conventional commits](https://www.conventionalcommits.org/):
  ```
  <type>[scope]: [<JIRA-KEY-TICKET>] <description>

  <General description of the changes>

  Changed files:
  - <path of the changed file>: <description of the change>
  ```
- When asked to open a pull request, write it in English, without co-authorship from any AI, with this structure:
  ```
  <type>[scope]: [<JIRA-KEY-TICKET>] <description>

  <General description of the changes>

  Changed files:
  - <path of the changed file>: <description of the change>

  Tests performed:
  - <test name>: <description of the test performed>
  ```

## Versioning rules
- The project follows [semantic versioning](https://semver.org/) `MAJOR.MINOR.PATCH`, and the source of truth
  is the `version` field of `pyproject.toml`; the Docker image is published with that version.
- The version is bumped when an epic or a task is finished, in a bump commit that also requires the developer's
  prior approval. The increment is set by the highest-impact commit type since the last version:
  - `MAJOR`: incompatible changes (`feat!`, `fix!` or `BREAKING CHANGE`), for example a removed endpoint or
    a change to the API contract.
  - `MINOR`: new compatible functionality (`feat`).
  - `PATCH`: fixes and changes without new functionality (`fix`, `perf`, `refactor`, `build`, `ci`, `chore`, etc.).
- The version is bumped with `uv version --bump <major|minor|patch>` (it updates `pyproject.toml` and `uv.lock`),
  in its own commit separate from the code changes: `chore(release): [<JIRA-KEY-TICKET>] Bump version to vX.Y.Z`.
- Tags are created only on `main`, on the merge commit, with the format `vX.Y.Z` (same as `pyproject.toml`) and
  annotated: `git tag -a vX.Y.Z -m "vX.Y.Z"`. A published tag is never moved or reused.
- The tag and the GitHub release are created by hand, never from a workflow, only after the `Release` workflow
  finishes successfully and with the developer's prior approval, using
  `gh release create vX.Y.Z --title "vX.Y.Z" --notes-file <file>`.
- Release notes are written in English, without co-authorship from any AI, with this structure:
  ```
  ## <Version summary>

  ### Features
  - <description> ([<JIRA-KEY-TICKET>])

  ### Fixes
  - <description> ([<JIRA-KEY-TICKET>])

  ### Other changes
  - <description> ([<JIRA-KEY-TICKET>])

  ### Database
  - <included migration and its impact, or "No migrations">

  ### Docker image
  - `<organization>/<image>:X.Y.Z` (`sha256:<digest>`)
  ```
- Version `1.0.0` is the project baseline: its tag is `v1.0.0` and its release summarizes the initial state.
