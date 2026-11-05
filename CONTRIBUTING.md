# Contributing

Two-person repo, but **public**, so some rules are hard constraints rather than style. Claude Code sessions follow the same rules (see `CLAUDE.md`).

## Never commit

- **Market data** in any form: raw `.csv.gz`, HDB partitions, parquet, pickles, or CSV extracts. The course data is not ours to redistribute. `data/` is gitignored; keep it that way.
- **The kdb license** (`kc.lic`, `k4.lic`, anything under `~/.kx`). It is tied to one person's KX account.
- **Credentials**: API keys, tokens, `.env` files.
- **Large generated output**: figures go in `output/` (gitignored). Only figures chosen for a report get copied into `reports/`.
- **Notebook outputs.** Clear outputs before committing, or install `nbstripout` so it happens automatically (see below).

## Branching

- `main` should always run. Don't push half-finished work to it.
- Do the work on short-lived branches named `<name>/<topic>`, e.g. `ethan/hdb-loader` or `<teammate>/leadership-var`.
- Open a pull request into `main`; the other person reviews and merges. For docs-only changes during ideation, pushing straight to `main` is fine.

```bash
git switch main && git pull
git switch -c ethan/hdb-loader
# ...work...
git add -p                      # stage hunk by hunk and read what you're committing
git commit -m "q: loader for trade/quote csv.gz via named pipe"
git push -u origin ethan/hdb-loader
# then open a PR on GitHub
```

## Commit messages

Prefix with the layer or area, then use the imperative mood:

```
q: add refresh-time grid function
py: residualize returns on rolling PC1
java: replay engine reads merged event stream from q
docs: record decision on 250ms grid
ideas: update 01 with VAR option
```

One logical change per commit. If the message needs "and", it is probably two commits.

## Where code goes

| Kind of work | Location |
|---|---|
| Anything that touches raw ticks or needs event-time joins | `q/` |
| Features, models, evaluation, plots | `python/notset/` (package) |
| Exploration | `python/notebooks/`. Once logic is reused, move it into the package |
| Stateful strategy simulation, latency, order lifecycle | `java/` |
| Parameters (windows, horizons, symbols, dates) | `config/*.yaml`, never hardcoded |
| Decisions and why | `docs/DECISIONS.md` |
| One line per run with a metric | `experiments/registry.jsonl` (appended by code, never edited by hand) |
| What a run taught us | `research/LEARNINGS.md` |

## Line endings

`.gitattributes` forces LF. If you're on Windows outside WSL, also run:

```bash
git config --global core.autocrlf input
```

## Notebook hygiene

```bash
pip install nbstripout
nbstripout --install        # run once inside the repo
```
