#!/usr/bin/env python3
"""Aggregate skill-usage from local JSONL logs — no server required.

Useful for a quick look at your own machine, or if members periodically ship
their ~/.claude/alin-skill-usage.jsonl files to a shared folder and you want a
lab-wide rollup without standing up the collector.

Usage:
    python3 aggregate_local.py [log1.jsonl log2.jsonl ...]
    # defaults to ~/.claude/alin-skill-usage.jsonl
"""

import json
import os
import sys
from collections import Counter


def load(paths):
    rows = []
    for p in paths:
        try:
            with open(os.path.expanduser(p), encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
        except FileNotFoundError:
            print(f"(skip, not found: {p})", file=sys.stderr)
    return rows


def main():
    paths = sys.argv[1:] or ["~/.claude/alin-skill-usage.jsonl"]
    rows = load(paths)
    if not rows:
        print("No events found.")
        return

    by_skill = Counter(r.get("skill") for r in rows)
    by_user = Counter(r.get("user") for r in rows)
    by_trigger = Counter(r.get("trigger") for r in rows)

    print(f"Total invocations: {len(rows)}\n")

    print("Most-used skills:")
    for skill, c in by_skill.most_common():
        print(f"  {c:5d}  {skill}")

    print("\nBy user:")
    for user, c in by_user.most_common():
        print(f"  {c:5d}  {user}")

    print("\nBy trigger:")
    for trig, c in by_trigger.most_common():
        print(f"  {c:5d}  {trig}")


if __name__ == "__main__":
    main()
