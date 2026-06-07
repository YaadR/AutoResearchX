"""
Template for [PROJECT_NAME] Evaluation Harness.

This script should:
1. Prepare the research environment (data generation, downloading, etc.).
2. Provide a fixed interface for evaluating candidates.
3. Be treated as read-only by the agent during the loop.

Usage:
    uv run prepare.py
    uv run prepare.py --force
"""

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path

# --- Configuration & Constants ---
PROJECT_NAME = "[PROJECT_NAME]"
DATA_VERSION = "v0"
# ... other constants ...

@dataclass
class EvaluationResult:
    """Structure for evaluation metrics."""
    score: float
    # ... other metrics ...

def prepare_environment(force: bool = False):
    """Setup data, benchmarks, or environment."""
    print(f"Preparing environment for {PROJECT_NAME}...")
    # ... logic here ...

def evaluate_candidate(candidate_dir: Path) -> EvaluationResult:
    """
    Evaluate the logic implemented in candidate_dir.
    This is the core interface used by the research loop.
    """
    # ... evaluation logic ...
    return EvaluationResult(score=0.0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Force preparation")
    args = parser.parse_args()
    
    prepare_environment(force=args.force)
