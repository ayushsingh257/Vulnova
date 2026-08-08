"""Vulnova Release Validation Runner Script."""

import sys
import os

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from tests.test_release_validation import run_standalone_release_validation

if __name__ == "__main__":
    sys.exit(run_standalone_release_validation())
