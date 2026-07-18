"""Run mutmut on the configured modules and enforce a mutation score threshold.

This script is part of the CI quality gate for critical domain modules.
mutmut 2.x does not expose a native threshold flag, so after running
`mutmut run` we read the results from the cache database (.mutmut-cache)
and exit with code 1 when the mutation score is below the required threshold.

mutmut 2.x stores every mutant in a single cache file without a module column,
so results from different modules cannot be separated in one cache. To keep each
module's mutation score independent we clear the cache before every `mutmut run`.

The mutation score threshold is the single source of truth shared with the
frontend Stryker gate. It lives in `mutation-threshold.json` at the repository
root and is resolved by `load_default_min_score()`. The threshold can be
overridden locally via the `MUTATION_SCORE_THRESHOLD` environment variable or
the `--min-score` CLI argument (highest priority).

Usage:
    python scripts/run_mutmut.py [--min-score 70] [--modules MODULE ...]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from mutmut.cache import Mutant, db_session, init_db

# Mutant statuses from mutmut (see mutmut/__init__.py)
OK_KILLED = "ok_killed"
BAD_SURVIVED = "bad_survived"
BAD_TIMEOUT = "bad_timeout"
OK_SUSPICIOUS = "ok_suspicious"
UNTESTED = "untested"
SKIPPED = "skipped"

# Fallback used only when the shared threshold file is missing.
FALLBACK_MIN_SCORE = 70

# Repository-root threshold file, shared with the frontend Stryker gate.
THRESHOLD_FILE = Path(__file__).resolve().parents[2] / "mutation-threshold.json"

DEFAULT_MODULES = [
    "app/modules/technical_analysis/signal_rating.py",
    "app/modules/signal_aggregation",
    "app/modules/strategy_generator",
]


def load_default_min_score() -> int:
    """Resolve the default mutation score threshold.

    Priority: ``--min-score`` (CLI) > ``MUTATION_SCORE_THRESHOLD`` (env) >
    ``mutation-threshold.json`` (repo root) > ``FALLBACK_MIN_SCORE``.

    Returns:
        The minimum acceptable mutation score in percent.
    """
    env_value = os.environ.get("MUTATION_SCORE_THRESHOLD")
    if env_value is not None:
        try:
            return int(env_value)
        except ValueError:
            print(
                f"Invalid MUTATION_SCORE_THRESHOLD={env_value!r}; falling back to the shared threshold file.",
                file=sys.stderr,
            )

    try:
        with THRESHOLD_FILE.open(encoding="utf-8") as fh:
            data = json.load(fh)
        return int(data["mutationScoreThreshold"])
    except (OSError, KeyError, ValueError, TypeError):
        print(
            f"Could not read mutation threshold from {THRESHOLD_FILE}; falling back to {FALLBACK_MIN_SCORE}%.",
            file=sys.stderr,
        )
        return FALLBACK_MIN_SCORE


# Known mutmut `run` exit codes (mutmut 2.x / 3.x). They are bit-OR combinable.
# 0 = all killed (success); 1 = fatal error; 2 = survivors; 4 = timeouts; 8 = suspicious (2x test time).
MUTMUT_KNOWN_EXIT_CODES = frozenset({0, 1, 2, 4, 8})

CACHE_PATH = Path(".mutmut-cache")


def _safe_clear_cache() -> None:
    """Remove the mutmut cache so each module's score is computed in isolation.

    Two handles can keep the SQLite cache file open on Windows (WinError 32):
      1. The parent process: Pony ORM binds `mutmut.cache.db` to the cache file
         inside `compute_score()` and keeps the connection open afterwards.
         We must `disconnect()` it before removing the file.
      2. The `mutmut run` subprocess: it may release its handle a moment after
         it returns. A short retry/backoff covers that race.
    """
    import time

    try:
        from mutmut.cache import db

        db.disconnect()
    except Exception:  # best-effort; ignore if already disconnected
        pass

    for attempt in range(5):
        try:
            CACHE_PATH.unlink(missing_ok=True)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.5 * (attempt + 1))


def run_mutmut(module: str) -> int:
    """Run `mutmut run` on the given module. Returns mutmut's exit code."""
    env = dict(os.environ)
    # Force UTF-8 for the subprocess. mutmut prints emoji (e.g. the celebration
    # glyph) that cannot be encoded on Windows consoles using a non-UTF-8 codepage,
    # which would otherwise crash the run with a UnicodeEncodeError.
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    # Pass the module via --paths-to-mutate (valid CLI flag and config key in mutmut 2.x).
    # Avoids relying on the positional argument, whose semantics differ across mutmut versions.
    command = [sys.executable, "-m", "mutmut", "run", "--paths-to-mutate", module]
    # S603: input is controlled (sys.executable + constant "mutmut" + a fixed default module path or a CI-provided arg)
    result = subprocess.run(command, env=env)  # noqa: S603
    return result.returncode


@init_db
@db_session
def compute_score() -> tuple[float, dict[str, int]]:
    """Read results from the mutmut cache and compute the mutation score.

    Mutation score = killed / (killed + survived + timeout + suspicious).
    Untested/skipped mutants do not lower the score.
    """
    counts: dict[str, int] = dict.fromkeys((OK_KILLED, BAD_SURVIVED, BAD_TIMEOUT, OK_SUSPICIOUS, UNTESTED, SKIPPED), 0)

    for mutant in Mutant.select():
        if mutant.status in counts:
            counts[mutant.status] += 1

    scored = counts[OK_KILLED] + counts[BAD_SURVIVED] + counts[BAD_TIMEOUT] + counts[OK_SUSPICIOUS]
    if scored == 0:
        return 0.0, counts

    score = 100.0 * counts[OK_KILLED] / scored
    return score, counts


def _run_module(module: str, min_score: int) -> tuple[bool, float, dict[str, int], int]:
    """Run mutmut for a single module with an isolated cache and return the outcome.

    Returns (passed, score, counts, run_returncode). The cache is removed before the
    run so that the score computed afterwards reflects only this module.
    """
    _safe_clear_cache()

    run_returncode = run_mutmut(module)
    score, counts = compute_score()

    killed = counts[OK_KILLED]
    survived = counts[BAD_SURVIVED]
    timeout = counts[BAD_TIMEOUT]
    suspicious = counts[OK_SUSPICIOUS]
    untested = counts[UNTESTED] + counts[SKIPPED]

    print("")
    print(f"=== Mutmut mutation score: {module} ===")
    print(f"Mutation score : {score:.1f}% (threshold >= {min_score}%)")
    print(f"Killed         : {killed}")
    print(f"Survived       : {survived}")
    print(f"Timeout        : {timeout}")
    print(f"Suspicious     : {suspicious}")
    print(f"Untested/Skip  : {untested}")

    # mutmut returns code 1 only on a fatal error (bad config, no tests, etc.).
    # Codes 2/4/8 (survivors/timeouts/suspicious) are expected outcomes and still
    # require reading the cache to compute the score. Any other (unknown) code means
    # mutmut aborted unexpectedly, so the cache may be stale -> fail hard before scoring.
    if run_returncode == 1:
        print("Mutmut fatal error (code 1).", file=sys.stderr)
        return False, score, counts, run_returncode
    if run_returncode not in MUTMUT_KNOWN_EXIT_CODES:
        print(
            f"Mutmut returned unexpected exit code {run_returncode}; "
            f"the cache may be stale. Known codes: {sorted(MUTMUT_KNOWN_EXIT_CODES)}.",
            file=sys.stderr,
        )
        return False, score, counts, run_returncode

    if score < min_score:
        print(
            f"Mutation score {score:.1f}% is below the {min_score}% threshold. "
            f"Improve tests to kill surviving mutants.",
            file=sys.stderr,
        )
        return False, score, counts, run_returncode

    print(f"Mutation score {score:.1f}% meets the {min_score}% threshold.")
    return True, score, counts, run_returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce a mutation score threshold via mutmut.")
    parser.add_argument(
        "--min-score",
        type=int,
        default=load_default_min_score(),
        help="Minimum acceptable mutation score in percent for every module "
        "(default: value from mutation-threshold.json at the repo root).",
    )
    parser.add_argument(
        "--modules",
        nargs="+",
        default=DEFAULT_MODULES,
        help="Space-separated module paths under mutation (default: signal_rating.py, signal_aggregation, strategy_generator).",  # noqa: E501
    )
    args = parser.parse_args()

    all_passed = True
    for module in args.modules:
        passed, _score, _counts, _rc = _run_module(module, args.min_score)
        all_passed = all_passed and passed

    print("")
    if all_passed:
        print(f"All {len(args.modules)} modules meet the {args.min_score}% mutation score threshold.")
        return 0

    print("One or more modules are below the mutation score threshold.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
