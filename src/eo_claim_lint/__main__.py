"""Entry point for ``python -m eo_claim_lint``."""

from __future__ import annotations

import sys

from eo_claim_lint.cli import main

if __name__ == "__main__":
    sys.exit(main())
