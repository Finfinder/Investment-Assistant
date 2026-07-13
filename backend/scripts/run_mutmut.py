"""Run mutmut on the configured module and enforce a mutation score threshold.

This script is part of the CI quality gate for the signal_rating.py module.
mutmut 2.x does not expose a native threshold flag, so after running
`mutmut run` we read the results from the cache database (.mutmut-cache)
and exit with code 1 when the mutation score is below the required threshold.

Usage:
    python scripts/run_mutmut.py [--min-score 70] [--module app/modules/technical_analysis/signal_rating.py]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from mutmut.cache import Mutant, db_session, init_db

# Mutant statuses from mutmut (see mutmut/__init__.py)
OK_KILLED = "ok_killed"
BAD_SURVIVED = "bad_survived"
BAD_TIMEOUT = "bad_timeout"
OK_SUSPICIOUS = "ok_suspicious"
UNTESTED = "untested"
SKIPPED = "skipped"

DEFAULT_MIN_SCORE = 70
DEFAULT_MODULE = "app/modules/technical_analysis/signal_rating.py"


def run_mutmut(module: str) -> int:
    """Run `mutmut run` on the given module. Returns mutmut's exit code."""
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    command = [sys.executable, "-m", "mutmut", "run", module]
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce a mutation score threshold via mutmut.")
    parser.add_argument(
        "--min-score",
        type=int,
        default=DEFAULT_MIN_SCORE,
        help="Minimum acceptable mutation score in percent (default 70).",
    )
    parser.add_argument(
        "--module",
        default=DEFAULT_MODULE,
        help="Path to the module under mutation (default signal_rating.py).",
    )
    args = parser.parse_args()

    run_returncode = run_mutmut(args.module)

    score, counts = compute_score()

    killed = counts[OK_KILLED]
    survived = counts[BAD_SURVIVED]
    timeout = counts[BAD_TIMEOUT]
    suspicious = counts[OK_SUSPICIOUS]
    untested = counts[UNTESTED] + counts[SKIPPED]

    print("")
    print("=== Mutmut mutation score ===")
    print(f"Mutation score : {score:.1f}% (threshold >= {args.min_score}%)")
    print(f"Killed         : {killed}")
    print(f"Survived       : {survived}")
    print(f"Timeout        : {timeout}")
    print(f"Suspicious     : {suspicious}")
    print(f"Untested/Skip  : {untested}")

    # mutmut returns code 1 on a fatal error; propagate it.
    if run_returncode == 1:
        print("Mutmut fatal error (code 1).", file=sys.stderr)
        return 1

    if score < args.min_score:
        print(
            f"Mutation score {score:.1f}% is below the {args.min_score}% threshold. "
            f"Improve tests to kill surviving mutants.",
            file=sys.stderr,
        )
        return 1

    print(f"Mutation score {score:.1f}% meets the {args.min_score}% threshold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
