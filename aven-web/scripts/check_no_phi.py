#!/usr/bin/env python3
"""Fail if files that look like real patient data or secrets are about to be committed.

Run it by hand (`python scripts/check_no_phi.py`), as a git pre-commit hook
(`sh scripts/install-hooks.sh`), and in CI. It checks tracked files, plus staged files
when run from the hook. It is a safety net, not a guarantee: the real rule is that
real patient data never goes on a developer machine or into this repo, only synthetic data.
"""

import re
import subprocess
import sys
from pathlib import Path

BLOCKED_SUFFIXES = {".835", ".837", ".x12", ".edi", ".era", ".hl7", ".cda", ".pem", ".key", ".p12", ".pfx"}
BLOCKED_NAMES = {".env"}
TEXT_SCAN_LIMIT = 2_000_000  # bytes

CONTENT_RULES = [
    # X12 interchange header (835/837/277 files all start with this)
    ("X12 EDI file header", re.compile(r"(?m)^ISA\*\d\d\*")),
    # US Social Security number written as 123-45-6789
    ("possible Social Security number", re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
]

SELF = Path(__file__).name


def git_files(staged_only: bool) -> list[Path]:
    cmd = (
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"]
        if staged_only
        else ["git", "ls-files"]
    )
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout  # noqa: S603
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Not a git repository; scanning nothing.")
        return []
    return [Path(line) for line in out.splitlines() if line.strip()]


def check(path: Path) -> list[str]:
    problems = []
    if path.name in BLOCKED_NAMES:
        problems.append("environment file with secrets (use .env.example for templates)")
    if path.suffix.lower() in BLOCKED_SUFFIXES:
        problems.append(f"blocked file type {path.suffix}")
    if path.name == SELF or not path.is_file():
        return problems
    try:
        text = path.read_bytes()[:TEXT_SCAN_LIMIT].decode("utf-8", errors="ignore")
    except OSError:
        return problems
    for label, pattern in CONTENT_RULES:
        if pattern.search(text):
            problems.append(label)
    return problems


def main() -> int:
    staged_only = "--staged" in sys.argv
    failed = False
    for path in git_files(staged_only):
        for problem in check(path):
            failed = True
            print(f"BLOCKED  {path}: {problem}")
    if failed:
        print("\nNothing sensitive may be committed. Remove the file or use synthetic data, then try again.")
        return 1
    print("check_no_phi: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
