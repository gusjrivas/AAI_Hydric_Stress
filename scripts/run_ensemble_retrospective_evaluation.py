"""CLI shim for the frozen retrospective ensemble evaluator."""

from experiment_runner.ensemble_retrospective_evaluation import main

if __name__ == "__main__":
    raise SystemExit(main())
