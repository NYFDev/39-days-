#!/usr/bin/env python3
"""Compatibility entrypoint for the single NYF schema-v2 aggregation builder."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    subprocess.run(["node", "aggregation/build.mjs"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
