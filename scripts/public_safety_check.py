"""Reject public-repository content that looks like private operational data."""
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", "__pycache__"}
BLOCKED_SUFFIXES = {".sqlite", ".db", ".pcap", ".pcapng"}
PATTERNS = {
    "private Windows path": re.compile(r"C:\\\\Users\\\\[^<][^\\\\]*", re.I),
    "IPv4 address": re.compile(r"(?<![\w.])(?:10|127|192\.168|172\.(?:1[6-9]|2\d|3[0-1]))(?:\.\d{1,3}){1,2}(?![\w.])"),
    "Bluetooth MAC address": re.compile(r"\b(?:[0-9A-F]{2}:){5}[0-9A-F]{2}\b", re.I),
    "likely API token": re.compile(r"\b(?:sk|api)[_-][A-Za-z0-9_-]{16,}\b", re.I),
    "password assignment": re.compile(r"\b(?:password|token|secret)\s*[:=]\s*['\"][^<'\"]+", re.I),
}


def files():
    for path in ROOT.rglob("*"):
        if any(part in SKIP_PARTS for part in path.parts) or not path.is_file():
            continue
        yield path


def main() -> int:
    findings = []
    for path in files():
        relative = path.relative_to(ROOT)
        if path.suffix.lower() in BLOCKED_SUFFIXES:
            findings.append(f"{relative}: blocked binary capture or database")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(f"{relative}: non-text file requires manual review")
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            for label, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append(f"{relative}:{line_number}: {label}")
    if findings:
        print("Public safety check failed:", *findings, sep="\n  ")
        return 1
    print("Public safety check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
