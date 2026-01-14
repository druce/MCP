# Repository Guidelines

## Project Structure & Module Organization

- `server.py` hosts the MCP server for research tools; it is the entry point for running the service.
- `skills/` contains standalone Python skills (research and portfolio management). Each script is executable and can be run directly.
- `templates/` stores Jinja2 report templates used by report-generation skills.
- `import/` is the drop zone for Fidelity CSV exports used by portfolio aggregation.
- `work/` holds per-symbol research outputs (e.g., `work/TSLA_20251222/`), and `logs/` stores runtime logs.
- `requirements.txt` captures Python dependencies; `CLAUDE.md` documents workflows and environment setup.

## Build, Test, and Development Commands

- `conda activate mcpskills` activates the Python 3.11 environment used by the skills and server.
- `pip install -r requirements.txt` installs Python dependencies.
- `python server.py` starts the MCP server locally; `mcp run server.py` runs via the MCP CLI.
- `./skills/research_stock.py TSLA --phases all` runs the full 7-phase research pipeline for a ticker.
- `./skills/aggregate_positions.py` aggregates Fidelity CSVs into `data/` (created on demand).
- `./skills/visualize_allocation.py` generates `dataviz/allocation_sunburst_YYYYMMDD.html` from aggregated data.

## Coding Style & Naming Conventions

- Use Python 3.11, 4-space indentation, and PEP 8 conventions.
- Prefer `snake_case` for functions/variables and `UPPER_SNAKE_CASE` for constants.
- Skills are CLI-first: include a top-of-file docstring with usage, use `argparse`, and keep error messages actionable.
- Templates in `templates/` use Jinja2; keep variable names aligned with skill outputs.

## Testing Guidelines

- No automated test suite is present yet. Validate changes by running the relevant skill and inspecting outputs under `work/`, `data/`, or `dataviz/`.
- When adding tests, keep them lightweight and colocate in a `tests/` directory using standard `test_*.py` naming.

## Commit & Pull Request Guidelines

- Commit messages in history are short and direct (e.g., `update README.md`, `skills`). Follow that pattern and keep the first line under ~50 chars.
- PRs should include a concise summary, the commands run, and links to generated artifacts (e.g., `work/{SYMBOL}_{YYYYMMDD}/` or `dataviz/*.html`) when relevant.

## Security & Configuration Tips

- Store API keys in a local `.env` file (`TIINGO_API_KEY`, `OPENBB_PAT`, `SEC_FIRM`, `SEC_USER`, `PERPLEXITY_API_KEY`).
- TA-Lib requires a system install on macOS (`brew install ta-lib`) before `pip install TA-Lib`.
